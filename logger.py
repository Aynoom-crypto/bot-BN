import logging
from colorama import init, Fore, Style

init(autoreset=True)

class ColoredLogger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(ch)
    
    def info(self, msg):
        self.logger.info(f"{Fore.GREEN}{msg}{Style.RESET_ALL}")
    
    def warning(self, msg):
        self.logger.warning(f"{Fore.YELLOW}{msg}{Style.RESET_ALL}")
    
    def error(self, msg):
        self.logger.error(f"{Fore.RED}{msg}{Style.RESET_ALL}")
    
    def signal(self, msg):
        self.logger.info(f"{Fore.CYAN}{'='*50}")
        self.logger.info(f"{Fore.CYAN}{msg}")
        self.logger.info(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
