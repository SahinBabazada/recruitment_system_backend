# flows/management/commands/create_flow_permissions.py

from django.core.management.base import BaseCommand
from flows.utils import create_flow_permissions  # Import your function

class Command(BaseCommand):
    """
    This is the required class that Django looks for.
    It must be named 'Command' and inherit from BaseCommand.
    """
    help = 'Creates the necessary permissions for the flows app.'

    def handle(self, *args, **kwargs):
        """
        The handle method is the entry point for the command's logic.
        """
        self.stdout.write("Starting the flow permission setup script...")
        
        # Here is where you call your function from utils.py
        create_flow_permissions()
        
        # Using self.style.SUCCESS provides nice green output
        self.stdout.write(self.style.SUCCESS('Successfully completed the permission setup.'))