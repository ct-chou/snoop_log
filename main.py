#!/usr/bin/env python3
"""
snoop_log — dog-perspective training agent

Commands:
  python main.py train <video>     Train on a session video
  python main.py command <audio>   Respond to an audio command
  python main.py show              Show all learned behaviors
  python main.py sessions          Show training session history
"""

import json
import os
import sys
from pathlib import Path

import anthropic
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from agent import analyze_training_session, respond_to_command, transcribe_audio
from log import (
    append_session,
    load_behaviors,
    load_sessions,
    next_session_id,
    save_behaviors,
)
from processor import extract_audio, process_video

console = Console()


def cmd_train(video_path: str) -> None:
    """Process a training session video and update learned behaviors."""
    path = Path(video_path)
    if not path.exists():
        console.print(f"[red]File not found:[/red] {video_path}")
        sys.exit(1)

    client = anthropic.Anthropic()
    session_id = next_session_id()

    console.print(f"\n[bold cyan]snoop_log[/bold cyan] — Training Session {session_id}")
    console.print(f"[dim]{path.name}[/dim]\n")

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("Extracting frames and audio...")
        video_data = process_video(video_path)
        p.update(t, description="[green]Frames and audio extracted")

        t = p.add_task("Transcribing audio...")
        transcript = transcribe_audio(video_data["audio_path"], client)
        os.unlink(video_data["audio_path"])
        p.update(t, description="[green]Audio transcribed")

        t = p.add_task("Analyzing session from dog's POV...")
        current_behaviors = load_behaviors()
        result = analyze_training_session(
            frames_b64=video_data["frames_b64"],
            transcript=transcript,
            current_behaviors=current_behaviors,
            session_id=session_id,
            client=client,
        )
        p.update(t, description="[green]Session analyzed")

    # Persist
    append_session({
        "session_id": session_id,
        "timestamp": result.get("timestamp"),
        "observations": result.get("observations"),
        "session_summary": result.get("session_summary"),
        "confusion_flags": result.get("confusion_flags", []),
    })
    save_behaviors(result.get("updated_behaviors", []))

    # Display
    console.print()
    console.print(Panel(
        result.get("observations", ""),
        title=f"[bold]Session {session_id} — Dog's Observations[/bold]",
        border_style="cyan",
    ))

    behaviors = result.get("updated_behaviors", [])
    if behaviors:
        console.print()
        table = Table(title="Learned Behaviors", border_style="dim", show_lines=True)
        table.add_column("Action", style="bold")
        table.add_column("Trigger Sound", max_width=30)
        table.add_column("Confidence", justify="right")
        table.add_column("Delta", justify="right")
        table.add_column("Reward History", max_width=25)

        for b in behaviors:
            delta = b.get("delta", "")
            if delta == "new":
                delta_str = "[yellow]new[/yellow]"
            elif delta.startswith("+"):
                delta_str = f"[green]{delta}[/green]"
            else:
                delta_str = f"[red]{delta}[/red]"

            table.add_row(
                b["action_id"],
                b.get("trigger_sound", ""),
                f"{b['confidence']:.2f}",
                delta_str,
                b.get("reward_history", ""),
            )
        console.print(table)

    if result.get("confusion_flags"):
        console.print()
        console.print("[yellow]Confusion:[/yellow]")
        for flag in result["confusion_flags"]:
            console.print(f"  [yellow]•[/yellow] {flag}")

    console.print()
    console.print(f"[dim italic]\"{result.get('session_summary', '')}\"[/dim italic]\n")


def cmd_command(audio_path: str) -> None:
    """Respond to an audio command from the owner."""
    path = Path(audio_path)
    if not path.exists():
        console.print(f"[red]File not found:[/red] {audio_path}")
        sys.exit(1)

    behaviors = load_behaviors()
    if not behaviors:
        console.print("[yellow]No learned behaviors yet. Run some training sessions first.[/yellow]")
        sys.exit(1)

    client = anthropic.Anthropic()

    console.print(f"\n[bold cyan]snoop_log[/bold cyan] — Command Received\n")

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("Listening and responding...")
        result = respond_to_command(audio_path, behaviors, client)
        p.update(t, description="[green]Done")

    console.print()
    console.print(f"[dim]Heard:[/dim] {result.get('command_transcript', '').splitlines()[0]}")
    console.print()

    recognized = result.get("recognized", False)
    confidence = result.get("confidence", 0.0)
    action_id = result.get("matched_action_id")

    if recognized:
        status = f"[green]Recognized[/green]: [bold]{action_id}[/bold] (confidence: {confidence:.2f})"
    else:
        status = f"[red]Not recognized[/red] (confidence: {confidence:.2f})"

    console.print(Panel(
        result.get("narration", ""),
        title=status,
        border_style="green" if recognized else "red",
    ))
    console.print()


def cmd_show() -> None:
    """Display all learned behaviors."""
    behaviors = load_behaviors()
    if not behaviors:
        console.print("[dim]No learned behaviors yet.[/dim]")
        return

    console.print(f"\n[bold cyan]snoop_log[/bold cyan] — Learned Behaviors ({len(behaviors)} total)\n")
    table = Table(border_style="dim", show_lines=True)
    table.add_column("Action", style="bold")
    table.add_column("Trigger Sound", max_width=35)
    table.add_column("Trigger Gesture", max_width=25)
    table.add_column("What I Do", max_width=35)
    table.add_column("Confidence", justify="right")
    table.add_column("Sessions", justify="right")

    for b in behaviors:
        sessions = ", ".join(str(s) for s in b.get("learned_in_sessions", []))
        table.add_row(
            b["action_id"],
            b.get("trigger_sound", ""),
            b.get("trigger_gesture") or "[dim]none[/dim]",
            b.get("action_description", ""),
            f"{b['confidence']:.2f}",
            sessions,
        )
    console.print(table)
    console.print()


def cmd_sessions() -> None:
    """Display training session history."""
    sessions = load_sessions()
    if not sessions:
        console.print("[dim]No sessions yet.[/dim]")
        return

    console.print(f"\n[bold cyan]snoop_log[/bold cyan] — Training History ({len(sessions)} sessions)\n")
    for s in sessions:
        flags = s.get("confusion_flags", [])
        flag_str = f"  [yellow]{len(flags)} confusion flag(s)[/yellow]" if flags else ""
        console.print(Panel(
            s.get("observations", ""),
            title=f"Session {s['session_id']} — {s.get('timestamp', '')}",
            subtitle=f"[dim italic]\"{s.get('session_summary', '')}\"[/dim italic]{flag_str}",
            border_style="dim",
        ))
    console.print()


def main() -> None:
    if len(sys.argv) < 2:
        console.print(__doc__)
        sys.exit(0)

    subcmd = sys.argv[1]

    if subcmd == "train" and len(sys.argv) >= 3:
        cmd_train(sys.argv[2])
    elif subcmd == "command" and len(sys.argv) >= 3:
        cmd_command(sys.argv[2])
    elif subcmd == "show":
        cmd_show()
    elif subcmd == "sessions":
        cmd_sessions()
    else:
        console.print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
