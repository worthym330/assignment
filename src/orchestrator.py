"""
Docker orchestration module for Formbricks lifecycle management.

Handles starting and stopping Formbricks using Docker Compose.
Uses subprocess to execute docker-compose commands for maximum compatibility.
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


class FormbricksOrchestrator:
    """Manages Formbricks Docker containers lifecycle."""
    
    def __init__(self, compose_file: Optional[Path] = None):
        """
        Initialize orchestrator.
        
        Args:
            compose_file: Path to docker-compose.yml. 
                         If None, uses docker-compose.yml in project root.
        """
        if compose_file is None:
            # Default to docker-compose.yml in project root
            base_dir = Path(__file__).parent.parent
            compose_file = base_dir / "docker-compose.yml"
        
        self.compose_file = compose_file
        
        if not self.compose_file.exists():
            raise FileNotFoundError(
                f"Docker Compose file not found: {self.compose_file}"
            )
    
    def _run_compose_command(
        self, 
        args: list[str], 
        check: bool = True,
        capture_output: bool = False
    ) -> subprocess.CompletedProcess:
        """
        Execute a docker-compose command.
        
        Args:
            args: Command arguments (e.g., ['up', '-d'])
            check: Raise exception on non-zero exit code
            capture_output: Capture stdout/stderr instead of showing
            
        Returns:
            CompletedProcess with result
        """
        cmd = [
            "docker-compose",
            "-f", str(self.compose_file),
            *args
        ]
        
        return subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True
        )
    
    def check_docker_available(self) -> bool:
        """
        Check if Docker and Docker Compose are available.
        
        Returns:
            True if both are available, False otherwise
        """
        try:
            # Check Docker
            subprocess.run(
                ["docker", "info"],
                capture_output=True,
                check=True
            )
            
            # Check Docker Compose
            subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                check=True
            )
            
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def is_running(self) -> bool:
        """
        Check if Formbricks containers are running.
        
        Returns:
            True if containers are up, False otherwise
        """
        try:
            result = self._run_compose_command(
                ["ps", "-q"],
                check=False,
                capture_output=True
            )
            
            # If there's output, containers are running
            return bool(result.stdout.strip())
        except Exception:
            return False
    
    def up(self, detach: bool = True, pull: bool = True) -> None:
        """
        Start Formbricks and all dependencies.
        
        Args:
            detach: Run containers in background
            pull: Pull latest images before starting
            
        Raises:
            RuntimeError: If Docker is not available
            subprocess.CalledProcessError: If docker-compose fails
        """
        if not self.check_docker_available():
            raise RuntimeError(
                "Docker or Docker Compose not found. Please ensure Docker is installed and running."
            )
        
        console.print("🐳 Starting Formbricks...", style="bold blue")
        
        # Pull images if requested
        if pull:
            console.print("📦 Pulling latest images (this may take a while on first run)...")
            try:
                self._run_compose_command(["pull"])
            except subprocess.CalledProcessError:
                console.print(
                    "⚠️  Failed to pull images. Continuing with existing images...",
                    style="yellow"
                )
        
        # Start services
        args = ["up"]
        if detach:
            args.append("-d")
        
        console.print("🚀 Starting containers...")
        self._run_compose_command(args)
        
        if detach:
            # Wait for health checks
            console.print("⏳ Waiting for services to be healthy...")
            self._wait_for_health()
            
            # Pull Ollama model if needed
            self._ensure_ollama_model()
            
            console.print("\n✅ Formbricks is running!", style="bold green")
            console.print(f"   URL: http://localhost:3000", style="cyan")
            console.print(f"   Ollama: http://localhost:11434", style="cyan")
            console.print("\n📝 Next steps:", style="bold")
            console.print("   1. Visit http://localhost:3000")
            console.print("   2. Complete the initial setup")
            console.print("   3. Create an API key (Settings → API Keys)")
            console.print("   4. Update .env with your API key and environment ID")
    
    def down(self, volumes: bool = False) -> None:
        """
        Stop Formbricks and clean up containers.
        
        Args:
            volumes: Also remove volumes (deletes all data!)
            
        Raises:
            subprocess.CalledProcessError: If docker-compose fails
        """
        if not self.is_running():
            console.print("ℹ️  Formbricks is not running", style="yellow")
            return
        
        console.print("🛑 Stopping Formbricks...", style="bold blue")
        
        args = ["down"]
        if volumes:
            args.append("-v")
            console.print("⚠️  Removing volumes (all data will be deleted)...", style="yellow")
        
        self._run_compose_command(args)
        
        console.print("✅ Formbricks stopped successfully", style="bold green")
        
        if not volumes:
            console.print(
                "💡 Data volumes preserved. Use 'formbricks up' to restart with existing data.",
                style="cyan"
            )
    
    def _wait_for_health(self, timeout: int = 120) -> None:
        """
        Wait for Formbricks to become healthy.
        
        Args:
            timeout: Maximum seconds to wait
            
        Raises:
            TimeoutError: If services don't become healthy in time
        """
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check if formbricks container is healthy
                result = subprocess.run(
                    [
                        "docker",
                        "inspect",
                        "--format={{.State.Health.Status}}",
                        "formbricks-app"
                    ],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0:
                    status = result.stdout.strip()
                    if status == "healthy":
                        return
                
            except Exception:
                pass
            
            time.sleep(5)
        
        # Timeout - give a warning but don't fail
        console.print(
            "⚠️  Health check timeout. Formbricks may still be starting...",
            style="yellow"
        )
        console.print(
            "   Check status with: docker-compose ps",
            style="yellow"
        )
    
    def _ensure_ollama_model(self, model: str = "llama2") -> None:
        """
        Ensure Ollama model is pulled in the container.
        
        Args:
            model: Model name to pull (default: llama2)
        """
        from .config import config
        model = config.OLLAMA_MODEL
        
        console.print(f"🤖 Checking Ollama model '{model}'...", style="cyan")
        
        try:
            # Check if model exists
            result = subprocess.run(
                ["docker", "exec", "formbricks-ollama", "ollama", "list"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if model in result.stdout:
                console.print(f"   ✓ Model '{model}' already available", style="green")
                return
            
            # Pull the model
            console.print(f"   📥 Pulling model '{model}' (this may take several minutes)...", style="yellow")
            subprocess.run(
                ["docker", "exec", "formbricks-ollama", "ollama", "pull", model],
                check=True
            )
            console.print(f"   ✓ Model '{model}' ready", style="green")
            
        except subprocess.CalledProcessError as e:
            console.print(
                f"   ⚠️  Failed to pull model: {e}",
                style="yellow"
            )
            console.print(
                f"   💡 You can pull it manually: docker exec formbricks-ollama ollama pull {model}",
                style="yellow"
            )
        except Exception as e:
            console.print(
                f"   ⚠️  Could not check Ollama: {e}",
                style="yellow"
            )
    
    def logs(self, follow: bool = False, service: Optional[str] = None) -> None:
        """
        Show container logs.
        
        Args:
            follow: Stream logs continuously
            service: Specific service to show logs for
        """
        args = ["logs"]
        
        if follow:
            args.append("-f")
        
        if service:
            args.append(service)
        
        self._run_compose_command(args, check=False)
    
    def status(self) -> None:
        """Show status of all containers."""
        self._run_compose_command(["ps"])
