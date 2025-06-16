# Flow Management Commands

This document describes the Django management commands for creating and managing approval flows.

## Commands Overview

### 1. `create_default_flow` - Create Default Flow Templates

Creates predefined flow templates that can be used as starting points for your approval workflows.

#### Basic Usage

```bash
# Create a simple approval flow
python manage.py create_default_flow

# Create and activate immediately
python manage.py create_default_flow --activate

# Create with custom name
python manage.py create_default_flow --name "My Custom Flow"

# Create different template types
python manage.py create_default_flow --template simple
python manage.py create_default_flow --template conditional
python manage.py create_default_flow --template comprehensive
```

#### Options

- `--name TEXT`: Custom name for the flow (default: "Default MPR Approval Flow")
- `--activate`: Activate the flow immediately after creation
- `--user USERNAME`: Specify the user who creates the flow (defaults to first superuser)
- `--template {simple,conditional,comprehensive}`: Choose template type (default: simple)
- `--force`: Force creation even if a flow with the same name exists

#### Template Types

**Simple Template:**
- Start → Manager Approval → Budget Holder Approval → End
- Basic linear approval process
- Good for straightforward workflows

**Conditional Template:**
- Start → Budget/Priority Check → High Priority (Executive) / Normal (Manager) → Notification → End
- Includes conditional routing based on budget amount and priority
- Demonstrates condition evaluation

**Comprehensive Template:**
- Start → Initial Notification → Routing Condition → Multiple Approval Paths → Final Notification → End
- Multi-stage approval with complex routing
- Shows notifications, conditions, and parallel approval paths

#### Examples

```bash
# Create a simple flow and activate it
python manage.py create_default_flow --template simple --activate --name "Basic Approval"

# Create a comprehensive flow for a specific user
python manage.py create_default_flow --template comprehensive --user john_doe --name "Enterprise Approval Flow"

# Override existing flow
python manage.py create_default_flow --force --name "Updated Flow"
```

### 2. `manage_flows` - Comprehensive Flow Management

Provides various operations for managing existing flows including listing, activation, testing, and cleanup.

#### Available Actions

```bash
python manage.py manage_flows <action> [options]
```

#### List Flows

```bash
# List all flows
python manage.py manage_flows list

# List only active flows
python manage.py manage_flows list --status active

# List with detailed information
python manage.py manage_flows list --detailed

# List draft flows
python manage.py manage_flows list --status draft
```

#### Activate/Deactivate Flows

```bash
# Activate a specific flow
python manage.py manage_flows activate 5

# Activate with specific user
python manage.py manage_flows activate 5 --user admin

# Deactivate current active flow
python manage.py manage_flows deactivate

# Deactivate with specific user
python manage.py manage_flows deactivate --user manager
```

#### Show Flow Details

```bash
# Show detailed information about a flow
python manage.py manage_flows show 3
```

#### Test Flow Execution

```bash
# Test flow with default MPR data
python manage.py manage_flows test 5

# Test with custom MPR data
python manage.py manage_flows test 5 --mpr-data '{"priority": "urgent", "budget_amount": 100000, "department": "Engineering"}'
```

#### Flow Statistics

```bash
# Show comprehensive statistics
python manage.py manage_flows stats
```

#### Cleanup Old Executions

```bash
# Preview what would be deleted (dry run)
python manage.py manage_flows cleanup --dry-run

# Delete executions older than 30 days
python manage.py manage_flows cleanup

# Delete executions older than 60 days
python manage.py manage_flows cleanup --days 60

# Dry run for 7 days
python manage.py manage_flows cleanup --days 7 --dry-run
```

## Setup Instructions

### 1. Create Management Command Directories

```bash
mkdir -p flows/management/commands
touch flows/management/__init__.py
touch flows/management/commands/__init__.py
```

### 2. Add the Command Files

Save the command files in the appropriate locations:
- `flows/management/commands/create_default_flow.py`
- `flows/management/commands/manage_flows.py`

### 3. Ensure Database Migrations

Make sure your flow models are migrated:

```bash
python manage.py makemigrations flows
python manage.py migrate flows
```

### 4. Create Initial Flow

```bash
# Create and activate a default flow
python manage.py create_default_flow --activate
```

## Usage Scenarios

### Initial Setup

```bash
# 1. Create a comprehensive default flow
python manage.py create_default_flow --template comprehensive --name "Main Approval Flow"

# 2. Check that it was created
python manage.py manage_flows list

# 3. Activate it
python manage.py manage_flows activate 1

# 4. Verify it's active
python manage.py manage_flows stats
```

### Development and Testing

```bash
# Test your flow with sample data
python manage.py manage_flows test 1 --mpr-data '{
  "priority": "urgent",
  "budget_amount": 85000,
  "employment_type": "permanent",
  "department": "Engineering"
}'

# Create a simple test flow
python manage.py create_default_flow --template simple --name "Test Flow"

# Check all flows
python manage.py manage_flows list --detailed
```

### Production Management

```bash
# Check system status
python manage.py manage_flows stats

# List all flows to see versions
python manage.py manage_flows list

# Activate a new version
python manage.py manage_flows activate 5 --user production_admin

# Clean up old executions monthly
python manage.py manage_flows cleanup --days 30
```

### Flow Updates

```bash
# Create new version of existing flow
python manage.py create_default_flow --template conditional --name "Updated Approval Flow v2"

# Test the new flow
python manage.py manage_flows test 6

# Activate when ready
python manage.py manage_flows activate 6

# Verify the switch
python manage.py manage_flows stats
```

## Best Practices

### 1. Flow Naming Convention
- Use descriptive names that indicate the flow purpose
- Include version numbers for major changes
- Examples: "Standard MPR Approval v2", "Executive Fast Track", "Contractor Approval"

### 2. Testing Before Activation
Always test flows before activating them:

```bash
# Test with various scenarios
python manage.py manage_flows test FLOW_ID --mpr-data '{"priority": "normal", "budget_amount": 25000}'
python manage.py manage_flows test FLOW_ID --mpr-data '{"priority": "urgent", "budget_amount": 100000}'
```

### 3. Backup Before Major Changes
- Export current flow configuration before major updates
- Keep a record of active flow IDs and activation dates

### 4. Regular Maintenance
- Review flow statistics monthly
- Clean up old executions regularly
- Monitor for failed executions

### 5. User Management
- Always specify the user when activating flows in production
- Use service accounts for automated operations
- Log all flow changes for audit purposes

## Troubleshooting

### Common Issues

**"No superuser found" Error:**
```bash
# Create a superuser first
python manage.py createsuperuser

# Or specify an existing user
python manage.py create_default_flow --user existing_username
```

**Flow Creation Fails:**
```bash
# Check if flow name already exists
python manage.py manage_flows list

# Use --force to override
python manage.py create_default_flow --force
```

**No Active Flow:**
```bash
# Check current status
python manage.py manage_flows stats

# Activate a flow
python manage.py manage_flows activate FLOW_ID
```

### Debugging Flow Issues

1. **Check Flow Structure:**
   ```bash
   python manage.py manage_flows show FLOW_ID
   ```

2. **Test Flow Logic:**
   ```bash
   python manage.py manage_flows test FLOW_ID --mpr-data '{"debug": "data"}'
   ```

3. **Review Statistics:**
   ```bash
   python manage.py manage_flows stats
   ```

## Integration with Application

The management commands are designed to work alongside your Django application. After creating flows using these commands:

1. **Frontend Integration:** Flows created via commands will appear in your web interface
2. **API Access:** Use the flows API to interact with flows programmatically  
3. **Execution:** MPRs submitted through your application will use the active flow
4. **Monitoring:** Use the web interface or API to monitor flow executions

## Security Considerations

- Restrict access to flow management commands in production
- Use specific user accounts for flow operations (audit trail)
- Regularly backup flow configurations
- Monitor flow execution logs for unusual patterns
- Validate MPR data before flow execution