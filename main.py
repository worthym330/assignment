#!/usr/bin/env python3
"""
Formbricks Data Seeder - Main CLI Entry Point

A production-ready CLI tool for orchestrating Formbricks locally
and seeding it with realistic LLM-generated survey data.

Usage:
    python main.py formbricks up        # Start Formbricks
    python main.py formbricks down      # Stop Formbricks
    python main.py formbricks generate  # Generate fake data
    python main.py formbricks seed      # Seed data into Formbricks
"""

import sys
from typing import Optional

import click
from rich.console import Console

from src.config import config
from src.generator import DataGenerator
from src.orchestrator import FormbricksOrchestrator
from src.seeder import FormbricksSeeder

console = Console()


# ============================================================================
# CLI Group Setup
# ============================================================================

@click.group()
def cli():
    """
    Formbricks Data Seeder
    
    Orchestrate Formbricks locally and seed with realistic data.
    """
    pass


@cli.group()
def formbricks():
    """Formbricks orchestration and data seeding commands."""
    pass


# ============================================================================
# Docker Orchestration Commands
# ============================================================================

@formbricks.command()
@click.option(
    "--no-pull",
    is_flag=True,
    help="Skip pulling latest images"
)
def up(no_pull: bool):
    """
    Start Formbricks locally using Docker Compose.
    
    This command:
    - Pulls latest Formbricks images (unless --no-pull)
    - Starts PostgreSQL database
    - Starts Formbricks application
    - Makes it accessible at http://localhost:3000
    
    Example:
        python main.py formbricks up
    """
    try:
        orchestrator = FormbricksOrchestrator()
        orchestrator.up(pull=not no_pull)
        
    except FileNotFoundError as e:
        console.print(f"❌ {e}", style="bold red")
        sys.exit(1)
        
    except RuntimeError as e:
        console.print(f"❌ {e}", style="bold red")
        console.print("\n💡 Install Docker: https://docs.docker.com/get-docker/", style="cyan")
        sys.exit(1)
        
    except Exception as e:
        console.print(f"❌ Failed to start Formbricks: {e}", style="bold red")
        console.print("\n🔍 Check logs with: docker-compose logs", style="yellow")
        sys.exit(1)


@formbricks.command()
@click.option(
    "--volumes",
    is_flag=True,
    help="Also remove data volumes (WARNING: deletes all data!)"
)
def down(volumes: bool):
    """
    Stop Formbricks and clean up containers.
    
    By default, data volumes are preserved so you can restart
    with existing data. Use --volumes to delete everything.
    
    Example:
        python main.py formbricks down
        python main.py formbricks down --volumes  # Delete all data
    """
    try:
        orchestrator = FormbricksOrchestrator()
        orchestrator.down(volumes=volumes)
        
    except Exception as e:
        console.print(f"❌ Failed to stop Formbricks: {e}", style="bold red")
        sys.exit(1)


# ============================================================================
# Data Generation Command
# ============================================================================

@formbricks.command()
@click.option(
    "--users",
    type=int,
    default=None,
    help=f"Number of users to generate (default: {config.NUM_USERS})"
)
@click.option(
    "--surveys",
    type=int,
    default=None,
    help=f"Number of surveys to generate (default: {config.NUM_SURVEYS})"
)
@click.option(
    "--model",
    type=str,
    default=None,
    help=f"Ollama model to use (default: {config.OLLAMA_MODEL})"
)
def generate(users: Optional[int], surveys: Optional[int], model: Optional[str]):
    """
    Generate realistic fake data using LLM.
    
    This command uses Ollama (local LLM) to generate:
    - User profiles (names, emails, roles)
    - Survey definitions (questions, types, choices)
    - Survey responses (realistic answers)
    
    Output is saved to data/ directory as JSON files.
    Does NOT interact with Formbricks - only generates data.
    
    Example:
        python main.py formbricks generate
        python main.py formbricks generate --users 20 --surveys 10
    """
    try:
        # Override config if specified
        if users:
            config.NUM_USERS = users
        if surveys:
            config.NUM_SURVEYS = surveys
        
        # Create generator
        generator = DataGenerator(model=model)
        
        # Generate all data
        generator.generate_all()
        
        console.print("\n✅ Success!", style="bold green")
        console.print(
            "📝 Next step: Run 'python main.py formbricks seed' to load this data into Formbricks",
            style="cyan"
        )
        
    except RuntimeError as e:
        console.print(f"\n❌ {e}", style="bold red")
        console.print("\n💡 Troubleshooting:", style="yellow")
        console.print("   1. Install Ollama: https://ollama.ai")
        console.print(f"   2. Pull model: ollama pull {config.OLLAMA_MODEL}")
        console.print("   3. Verify Ollama is running: ollama list")
        sys.exit(1)
        
    except Exception as e:
        console.print(f"\n❌ Generation failed: {e}", style="bold red")
        import traceback
        console.print(traceback.format_exc(), style="dim")
        sys.exit(1)


# ============================================================================
# Data Seeding Command
# ============================================================================

@formbricks.command()
@click.option(
    "--api-key",
    type=str,
    default=None,
    help="Formbricks API key (overrides .env)"
)
@click.option(
    "--environment-id",
    type=str,
    default=None,
    help="Formbricks environment ID (overrides .env)"
)
def seed(api_key: Optional[str], environment_id: Optional[str]):
    """
    Seed generated data into Formbricks via APIs.
    
    This command:
    - Reads JSON files from data/ directory
    - Creates users via Management API (if supported)
    - Creates surveys via Management API
    - Submits responses via Client API
    
    Requires:
    - Formbricks running (python main.py formbricks up)
    - API key and environment ID in .env
    - Generated data files in data/
    
    Example:
        python main.py formbricks seed
    """
    try:
        # Create seeder
        seeder = FormbricksSeeder(
            api_key=api_key,
            environment_id=environment_id
        )
        
        # Seed all data
        seeder.seed_all()
        
        console.print("\n✅ Success!", style="bold green")
        console.print(
            f"🌐 View your dashboard: {config.FORMBRICKS_URL}",
            style="cyan"
        )
        
    except ValueError as e:
        console.print(f"\n❌ Configuration error: {e}", style="bold red")
        console.print("\n💡 Setup instructions:", style="yellow")
        console.print("   1. Visit http://localhost:3000")
        console.print("   2. Complete initial setup")
        console.print("   3. Go to Settings → API Keys")
        console.print("   4. Create a new API key")
        console.print("   5. Update .env with API key and environment ID")
        sys.exit(1)
        
    except FileNotFoundError as e:
        console.print(f"\n❌ {e}", style="bold red")
        console.print(
            "\n💡 Run 'python main.py formbricks generate' first to create data files",
            style="yellow"
        )
        sys.exit(1)
        
    except ConnectionError as e:
        console.print(f"\n❌ {e}", style="bold red")
        console.print(
            "\n💡 Start Formbricks with: python main.py formbricks up",
            style="yellow"
        )
        sys.exit(1)
        
    except Exception as e:
        console.print(f"\n❌ Seeding failed: {e}", style="bold red")
        import traceback
        console.print(traceback.format_exc(), style="dim")
        sys.exit(1)


# ============================================================================
# Utility Commands
# ============================================================================

@formbricks.command()
def status():
    """
    Show status of Formbricks containers.
    
    Example:
        python main.py formbricks status
    """
    try:
        orchestrator = FormbricksOrchestrator()
        
        if orchestrator.is_running():
            console.print("✅ Formbricks is running", style="bold green")
            console.print(f"   URL: {config.FORMBRICKS_URL}", style="cyan")
            console.print("\n📊 Container status:", style="bold")
            orchestrator.status()
        else:
            console.print("⚠️  Formbricks is not running", style="yellow")
            console.print(
                "   Start with: python main.py formbricks up",
                style="cyan"
            )
        
    except Exception as e:
        console.print(f"❌ Failed to check status: {e}", style="bold red")
        sys.exit(1)


@formbricks.command()
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    help="Follow log output"
)
@click.option(
    "--service",
    type=str,
    default=None,
    help="Show logs for specific service (formbricks, postgres)"
)
def logs(follow: bool, service: Optional[str]):
    """
    Show container logs.
    
    Example:
        python main.py formbricks logs
        python main.py formbricks logs --follow
        python main.py formbricks logs --service formbricks
    """
    try:
        orchestrator = FormbricksOrchestrator()
        orchestrator.logs(follow=follow, service=service)
        
    except Exception as e:
        console.print(f"❌ Failed to show logs: {e}", style="bold red")
        sys.exit(1)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point with global error handling."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n\n⚠️  Interrupted by user", style="yellow")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n❌ Unexpected error: {e}", style="bold red")
        import traceback
        console.print(traceback.format_exc(), style="dim")
        sys.exit(1)


if __name__ == "__main__":
    main()
