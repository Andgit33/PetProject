#!/usr/bin/env python3
"""
Command-line interface for Road Trip Planner
"""
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path
from src.build_index import DestinationIndex
from src.query import TripPlanner

app = typer.Typer(help="Road Trip Planner - Find destinations based on your preferences")
console = Console()

@app.command()
def build():
    """Build the destination index from JSON files."""
    console.print("[bold green]Building destination index...[/bold green]")
    try:
        index = DestinationIndex()
        index.build_index()
        console.print("[bold green]✓ Index built successfully![/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)

@app.command()
def search(
    query: str = typer.Argument(..., help="Your travel query"),
    top_k: int = typer.Option(5, "--top", "-k", help="Number of results to return")
):
    """Search for destinations matching your query."""
    console.print(f"[bold cyan]Searching for:[/bold cyan] {query}\n")
    
    try:
        planner = TripPlanner()
        results = planner.search_destinations(query, top_k=top_k)
        
        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return
        
        # Create results table
        table = Table(title="Top Destinations", show_header=True, header_style="bold magenta")
        table.add_column("Rank", style="dim", width=4)
        table.add_column("Destination", style="cyan", width=25)
        table.add_column("Location", style="magenta", width=20)
        table.add_column("Score", style="green", width=8)
        
        for i, result in enumerate(results, 1):
            table.add_row(
                str(i),
                result['destination'],
                result['location'],
                f"{result['score']:.3f}"
            )
        
        console.print(table)
        
        # Show top result details
        if results:
            console.print("\n")
            top_result = results[0]
            details = Panel(
                top_result['explanation'],
                title=f"[bold green]Top Match: {top_result['destination']}[/bold green]",
                border_style="green"
            )
            console.print(details)
            
            # Show score breakdown
            score_table = Table(title="Score Breakdown", show_header=True)
            score_table.add_column("Aspect", style="cyan")
            score_table.add_column("Score", style="green")
            score_table.add_row("Activities", f"{top_result['activities_score']:.3f}")
            score_table.add_row("Scenery", f"{top_result['scenery_score']:.3f}")
            score_table.add_row("Amenities", f"{top_result['amenities_score']:.3f}")
            score_table.add_row("Location", f"{top_result['location_score']:.3f}")
            score_table.add_row("Combined", f"{top_result['score']:.3f}")
            console.print("\n")
            console.print(score_table)
    
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)

@app.command()
def interactive():
    """Start an interactive search session."""
    console.print("[bold green]Road Trip Planner - Interactive Mode[/bold green]")
    console.print("[dim]Type 'quit' or 'exit' to end the session[/dim]\n")
    
    try:
        planner = TripPlanner()
    except Exception as e:
        console.print(f"[bold red]Error loading planner:[/bold red] {e}")
        console.print("[yellow]Make sure you've built the index first with: python -m src.cli build[/yellow]")
        raise typer.Exit(1)
    
    while True:
        query = typer.prompt("\n[cyan]What kind of destination are you looking for?[/cyan]")
        
        if query.lower() in ['quit', 'exit', 'q']:
            console.print("[bold green]Happy travels! 🗺️[/bold green]")
            break
        
        try:
            results = planner.search_destinations(query, top_k=3)
            
            if not results:
                console.print("[yellow]No results found. Try a different query.[/yellow]")
                continue
            
            # Show top 3 results
            for i, result in enumerate(results, 1):
                console.print(f"\n[bold cyan]{i}. {result['destination']}[/bold cyan] - {result['location']}")
                console.print(f"   Score: [green]{result['score']:.3f}[/green]")
                console.print(f"   {result['explanation'][:200]}...")
        
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    app()

