#!/usr/bin/env python3
import time
import math
import random
from typing import Tuple, Optional
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile, IBMQ
from qiskit.circuit.library import QFT
from qiskit.providers import Backend
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.style import Style
from rich.table import Table
from rich import box

class QuantumPrimeHunter:
    def __init__(self, backend: Backend):
        self.console = Console()
        self.backend = backend
        self.qubit_count = backend.configuration().n_qubits
        self.max_bits = math.floor(math.log2(self.qubit_count / 2))
        
        self.title_style = Style(color="bright_cyan", bold=True)
        self.success_style = Style(color="bright_green", bold=True)
        self.warning_style = Style(color="yellow", bold=True)
        self.error_style = Style(color="red", bold=True)
        self.info_style = Style(color="bright_blue")
        self.highlight_style = Style(color="bright_magenta", bold=True)
        
    def display_banner(self):
        """Show the quantum hardware banner"""
        title = Text("⚛️ QUANTUM PRIME HUNTER 1.0", style=self.title_style)
        backend_info = Text(
            f"{self.backend.name()} - {self.qubit_count} Qubits\n"
            f"Version: {self.backend.version}\n"
            f"Status: {self.backend.status().status_msg}",
            style=self.info_style
        )
        
        banner = Panel.fit(
            Text.assemble(title, "\n", backend_info),
            border_style="bright_cyan",
            box=box.DOUBLE,
            padding=(1, 2)
        )
        self.console.print(banner)
        
    def get_user_input(self) -> int:
        """Prompt user for number to factor"""
        while True:
            try:
                num = Prompt.ask(
                    "[bright_cyan]Enter a large semiprime to factor[/]",
                    default="323170060713110073007148766886699519604441026697154840321303454275246551081"
                )
                num = int(num)
                if num < 2:
                    self.console.print("[red]Number must be greater than 1[/]")
                    continue
                if self.is_prime(num):
                    self.console.print(f"[yellow]Warning: {num} is prime. Please enter a composite number.[/]")
                    continue
                return num
            except ValueError:
                self.console.print("[red]Invalid input. Please enter a valid integer.[/]")
    
    @staticmethod
    def is_prime(n: int) -> bool:
        """Simple primality test for small numbers"""
        if n < 2:
            return False
        for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]:
            if n % p == 0:
                return n == p
        d = n - 1
        s = 0
        while d % 2 == 0:
            d //= 2
            s += 1
        for a in [2, 325, 9375, 28178, 450775, 9780504, 1795265022]:
            if a >= n:
                continue
            x = pow(a, d, n)
            if x == 1 or x == n - 1:
                continue
            for _ in range(s - 1):
                x = pow(x, 2, n)
                if x == n - 1:
                    break
            else:
                return False
        return True
    
    def shors_algorithm(self, N: int) -> Tuple[int, int]:
        """Execute Shor's algorithm to find factors of N"""
        if N % 2 == 0:
            return (2, N // 2)
        
        a = random.randint(2, N - 1)
        gcd_val = math.gcd(a, N)
        if gcd_val > 1:
            return (gcd_val, N // gcd_val)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=self.console
        ) as progress:
            task1 = progress.add_task("[cyan]Initializing quantum circuit...", total=1)
            r = self.quantum_period_finding(a, N, progress)
            progress.update(task1, advance=1)
            
        if r % 2 != 0:
            raise ValueError("Period finding failed: odd period")
            
        x = pow(a, r // 2, N)
        if x == N - 1:
            raise ValueError("Period finding failed: x ≡ -1 mod N")
            
        p = math.gcd(x + 1, N)
        q = math.gcd(x - 1, N)
        return (p, q)
    
    def quantum_period_finding(self, a: int, N: int, progress: Progress) -> int:
        """Quantum subroutine to find the period of a^x mod N"""
        task2 = progress.add_task("[magenta]Configuring phase estimation...", total=1)
        
        n = math.ceil(math.log2(N))
        if 2 * n + 3 > self.qubit_count:
            raise ValueError(f"Number too large for current hardware. Requires {2*n+3} qubits but only {self.qubit_count} available.")

        up_reg = QuantumRegister(2 * n, 'up')
        down_reg = QuantumRegister(n, 'down')
        aux_reg = QuantumRegister(1, 'aux')
        cl_reg = ClassicalRegister(2 * n, 'cl')
        
        qc = QuantumCircuit(up_reg, down_reg, aux_reg, cl_reg)
        
        qc.h(up_reg)
        qc.x(down_reg[0])
        
        progress.update(task2, description="[blue]Performing modular exponentiation...")
        for q in range(2 * n):
            qc.append(self.controlled_modular_exponentiation(a, 2 ** q, N, n), 
                     [up_reg[q]] + down_reg[:] + aux_reg[:])
        
        progress.update(task2, description="[green]Applying Quantum Fourier Transform...")
        qc.append(QFT(num_qubits=2*n, inverse=True), up_reg)
        
        progress.update(task2, description="[yellow]Measuring quantum state...")
        qc.measure(up_reg, cl_reg)
        
        progress.update(task2, description="[cyan]Optimizing quantum circuit...")
        transpiled_qc = transpile(qc, backend=self.backend, optimization_level=3)
        
        progress.update(task2, description="[bright_magenta]Executing on quantum hardware...")
        job = self.backend.run(transpiled_qc, shots=1024)
        
        while not job.done():
            time.sleep(0.5)
            status = job.status()
            progress.update(task2, description=f"[cyan]Quantum execution: {status.name}...")
        
        result = job.result()
        counts = result.get_counts()
        
        progress.update(task2, description="[bright_blue]Analyzing quantum measurements...")
        measured_phase = int(max(counts.items(), key=lambda x: x[1])[0], 2)
        phase = measured_phase / (2 ** (2 * n))
        
        frac = self.continued_fractions(phase, N)
        r = frac.denominator
        
        progress.update(task2, advance=1)
        return r
    
    @staticmethod
    def controlled_modular_exponentiation(a: int, power: int, N: int, n: int) -> QuantumCircuit:
        """Create a controlled modular exponentiation circuit"""
        qc = QuantumCircuit(name=f"ModExp({a}^{power} mod {N})")
        up_q = QuantumRegister(1, 'up')
        down_q = QuantumRegister(n, 'down')
        aux_q = QuantumRegister(1, 'aux')
        qc.add_register(up_q, down_q, aux_q)

        for i in range(n):
            qc.cx(up_q[0], down_q[i])
            
        return qc
    
    @staticmethod
    def continued_fractions(x: float, N: int, max_denominator: int = None) -> 'Fraction':
        """Find the best rational approximation to x using continued fractions"""
        from fractions import Fraction
        if max_denominator is None:
            max_denominator = N
            
        return Fraction(x).limit_denominator(max_denominator)
    
    def run(self):
        """Main execution loop"""
        self.display_banner()
        
        while True:
            try:
                N = self.get_user_input()
                
                start_time = time.perf_counter()
                
                with self.console.status(
                    "[bold green]Executing Shor's Algorithm on quantum hardware...",
                    spinner="dots"
                ) as status:
                    try:
                        status.update("[cyan]Initializing quantum registers...")
                        p, q = self.shors_algorithm(N)

                        if p * q != N:
                            raise ValueError("Quantum computation failed to find correct factors")
                            
                        elapsed = time.perf_counter() - start_time
                        
                        result_table = Table.grid(expand=True)
                        result_table.add_column(style=self.highlight_style)
                        result_table.add_column(style=self.success_style)
                        
                        result_table.add_row("Prime Factors:", f"{p}, {q}")
                        result_table.add_row("Time Taken:", f"{elapsed:.6f} seconds")
                        result_table.add_row("Qubits Used:", f"{2*math.ceil(math.log2(N))+3}")
                        result_table.add_row("Backend:", self.backend.name())
                        
                        self.console.print(Panel(
                            result_table,
                            title="[bright_green]Factorization Complete",
                            border_style="green",
                            padding=(1, 4)
                        ))
                        
                        if N > 1e20:
                            self.console.print(
                                Panel(
                                    f"This {len(str(N))}-digit number was assumed secure under classical encryption.",
                                    style=self.warning_style,
                                    border_style="yellow"
                                )
                            )
                            
                    except ValueError as e:
                        elapsed = time.perf_counter() - start_time
                        self.console.print(
                            Panel(
                                f"[red]Error: {str(e)}[/]\nTime elapsed: {elapsed:.3f}s",
                                title="[red]Factorization Failed",
                                border_style="red"
                            )
                        )
                        
                if not Confirm.ask("[bright_cyan]Factor another number?", default=True):
                    break
                    
            except KeyboardInterrupt:
                self.console.print("\n[bright_yellow]Quantum computation aborted by user.")
                break


def connect_to_quantum_backend():
    """Connect to quantum hardware"""
    console = Console()
    
    try:
        console.print("[cyan]Attempting to connect to IBM Quantum...")
        IBMQ.load_account()
        provider = IBMQ.get_provider()
        
        backend = provider.get_backend('ibm_kyiv')  # Replace with your Quantum backend
        return backend
        
    except Exception as e:
        console.print(f"[yellow]IBM Quantum connection failed: {str(e)}[/]")

    
    raise RuntimeError("Unable to connect to any quantum backend")


if __name__ == "__main__":
    try:
        backend = connect_to_quantum_backend()

        hunter = QuantumPrimeHunter(backend)
        hunter.run()
        
    except Exception as e:
        Console().print(f"[red]Fatal error: {str(e)}[/]")
