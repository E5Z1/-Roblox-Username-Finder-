import requests
import random
import string
import time
import concurrent.futures
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table
from rich.live import Live
from rich.prompt import Prompt

console = Console()
working_proxies = set()  


def fetch_proxies(country_code='de', max_results=20):
    url = f"https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&country={country_code}&ssl=all&anonymity=all&limit={max_results}"
    try:
        response = requests.get(url)
        if response.ok:
            proxies = response.text.strip().split('\r\n')
            return [proxy for proxy in proxies if proxy]  
    except requests.RequestException as err:
        console.print(f"[red]⚠️ Error fetching proxies: {err}[/red]")  
    return []  

# Random Words  
def get_random_words(min_len=3, max_len=5, amount=100):
    api_url = f"https://random-word-api.herokuapp.com/word?number={amount}"
    try:
        response = requests.get(api_url)
        if response.ok:
            words = response.json()
            return [word for word in words if min_len <= len(word) <= max_len]  
    except requests.RequestException as err:
        console.print(f"[red]⚠️ Couldn't fetch word list: {err}[/red]")
    return []

#Roblox username checker
def check_roblox_username(username, proxy=None):
    url = f"https://auth.roblox.com/v1/usernames/validate?request.username={username}&request.birthday=2000-01-01"
    try:
        response = requests.get(url, proxies={'http': f'http://{proxy}', 'https': f'http://{proxy}'} if proxy else None, timeout=5)
        if response.status_code == 200:
            return username if response.json().get('code') == 0 else None  
        elif response.status_code == 429:
            time.sleep(0.2)  # if rate-limited slow down nigga !?
    except requests.RequestException:
        if proxy:
            working_proxies.discard(proxy)  # Remove shitty bad proxy
    return None  

# Generate a random username
def create_username(min_chars, max_chars, use_dict_words=False):
    length = random.randint(min_chars, max_chars)  # Pick a random length faster pls 😭
    if use_dict_words:
        word_list = get_random_words(min_len=length, max_len=length)
        return random.choice(word_list) if word_list else None  # Use word list if available
    char_pool = string.ascii_letters + string.digits + '_'
    return ''.join(random.choices(char_pool, k=length))  # Otherwise generate a random username


def search_for_usernames(target_count=5, enable_proxies=True, words_mode=False, min_chars=5, max_chars=20):
    found = []
    attempts = 0  # Track how many names we check
    
    progress = Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TextColumn("[blue]{task.fields[status]}"),
    )
    
    task = progress.add_task("[cyan]Scanning usernames...", total=target_count, status="Starting...")

    def validate_single_username():
        nonlocal attempts
        new_name = create_username(min_chars, max_chars, words_mode)
        if not new_name:
            return None
        proxy = random.choice(list(working_proxies)) if enable_proxies and working_proxies else None
        progress.update(task, description=f"[cyan]Checking[/cyan] [yellow]{new_name}[/yellow]")
        result = check_roblox_username(new_name, proxy)
        attempts += 1
        progress.update(task, status=f"Checked: {attempts}")
        return result

    with Live(progress, refresh_per_second=10):
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            while len(found) < target_count:
                if enable_proxies and not working_proxies:
                    console.print("[yellow]🔍 Gathering fresh proxies...[/yellow]")
                    working_proxies.update(fetch_proxies())
                    if not working_proxies:
                        console.print("[red]❌ No proxies found, switching to direct requests[/red]")
                        enable_proxies = False
                
                batch_size = min(50, target_count - len(found))
                futures = [executor.submit(validate_single_username) for _ in range(batch_size)]
                
                for future in concurrent.futures.as_completed(futures):
                    if (username := future.result()):
                        found.append(username)
                        progress.update(task, advance=1, status=f"Found: {username}")
                        if len(found) >= target_count:
                            break

    return found, attempts

# Main
def main():
    console.clear()
    console.print(Panel.fit(
        "[bold green]🌟 Roblox Username Finder 🌟[/bold green]",
        subtitle="A tool to find available Roblox usernames",
        border_style="bright_white",
        padding=(1, 1)
    ))

    enable_proxies = Prompt.ask("[yellow]🔒 Use proxies to avoid rate limits?[/yellow]", choices=["yes", "no"], default="yes") == "yes"
    use_words = Prompt.ask("[yellow]📚 Use dictionary words instead of random letters?[/yellow]", choices=["yes", "no"], default="no")
    
    min_length = int(Prompt.ask("[yellow]📏 Minimum username length?[/yellow]", default="5"))
    max_length = int(Prompt.ask("[yellow]📏 Maximum username length?[/yellow]", default="20"))

    if enable_proxies:
        console.print("[cyan]🌐 Fetching proxies...[/cyan]")
        working_proxies.update(fetch_proxies())
        console.print(f"[cyan]✅ Found {len(working_proxies)} proxies[/cyan]")
    else:
        console.print("[cyan]⚠️ Proxies disabled, might hit rate limits[/cyan]")
    
    num_usernames = int(Prompt.ask("[yellow]🎯 How many usernames should we find?[/yellow]", default="5"))
    
    console.print("\n[cyan]🔍 Beginning search...[/cyan]")
    found_names, total_checks = search_for_usernames(num_usernames, enable_proxies, use_words, min_length, max_length)
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Available Usernames", style="cyan")
    table.add_column("Total Attempts", style="green")
    table.add_column("Success Rate", style="yellow")
    
    for name in found_names:
        table.add_row(name, "", "")
    
    success_percentage = (len(found_names) / total_checks) * 100 if total_checks > 0 else 0
    table.add_row("", str(total_checks), f"{success_percentage:.1f}%")
    
    console.print(Panel(table, title="[bold]🏆 Results[/bold]", expand=False))
    
    if enable_proxies:
        console.print(f"\n[cyan]🔌 {len(working_proxies)} proxies still functional:[/cyan]")
        for proxy in working_proxies:
            console.print(f"- {proxy}")

    console.print("\n[bold yellow]🎉 Happy username hunting![/bold yellow]")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
