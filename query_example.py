#!/usr/bin/env python3
"""
Example script for querying destinations
"""
from src.query import TripPlanner
from rich.console import Console
from rich.table import Table

def main():
    console = Console()
    
    # Initialize planner
    console.print("[bold green]Loading trip planner...[/bold green]")
    planner = TripPlanner()
    
    # Example queries
    queries = [
        "I want to go hiking in the mountains with scenic views",
        "Beach destination with water sports and good restaurants",
        "National park with camping and wildlife viewing"
    ]
    
    for query in queries:
        console.print(f"\n[bold cyan]Query:[/bold cyan] {query}")
        console.print("[bold yellow]Results:[/bold yellow]\n")
        
        results = planner.search_destinations(query, top_k=3)
        
        # Create table
        table = Table(title="Top Destinations")
        table.add_column("Destination", style="cyan")
        table.add_column("Location", style="magenta")
        table.add_column("Score", style="green")
        table.add_column("Activities", style="blue")
        table.add_column("Scenery", style="blue")
        
        for result in results:
            table.add_row(
                result['destination'],
                result['location'],
                f"{result['score']:.3f}",
                f"{result['activities_score']:.3f}",
                f"{result['scenery_score']:.3f}"
            )
        
        console.print(table)
        
        # Show top result details
        if results:
            console.print(f"\n[bold]Top Match:[/bold] {results[0]['destination']}")
            console.print(results[0]['explanation'])

if __name__ == "__main__":
    main()

