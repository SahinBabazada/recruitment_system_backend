# mpr/migrations/0002_add_organizational_roles.py
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mpr', '0001_initial'),
    ]

    operations = [
        # Create role tables
        migrations.CreateModel(
            name='Recruiter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_primary', models.BooleanField(default=False, help_text='Primary recruiter for this unit')),
                ('specialization', models.CharField(blank=True, help_text='e.g., Technical roles, Sales roles', max_length=200)),
                ('is_active', models.BooleanField(default=True)),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('assigned_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_recruiters', to=settings.AUTH_USER_MODEL)),
                ('organizational_unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recruiters', to='mpr.organizationalunit')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recruiter_roles', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'mpr_recruiters',
                'ordering': ['-is_primary', 'user__first_name'],
            },
        ),
        migrations.CreateModel(
            name='Manager',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_primary', models.BooleanField(default=False, help_text='Primary manager for this unit')),
                ('manager_type', models.CharField(choices=[('line_manager', 'Line Manager'), ('functional_manager', 'Functional Manager'), ('project_manager', 'Project Manager'), ('department_head', 'Department Head')], default='line_manager', max_length=50)),
                ('is_active', models.BooleanField(default=True)),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('assigned_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_managers', to=settings.AUTH_USER_MODEL)),
                ('organizational_unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='managers', to='mpr.organizationalunit')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='manager_roles', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'mpr_managers',
                'ordering': ['-is_primary', 'user__first_name'],
            },
        ),
        migrations.CreateModel(
            name='BudgetHolder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_primary', models.BooleanField(default=False, help_text='Primary budget holder for this unit')),
                ('budget_limit', models.DecimalField(blank=True, decimal_places=2, help_text='Budget limit in local currency', max_digits=12, null=True)),
                ('budget_type', models.CharField(choices=[('operational', 'Operational Budget'), ('project', 'Project Budget'), ('hiring', 'Hiring Budget'), ('capex', 'Capital Expenditure')], default='operational', max_length=50)),
                ('is_active', models.BooleanField(default=True)),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('assigned_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_budget_holders', to=settings.AUTH_USER_MODEL)),
                ('organizational_unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='budget_holders', to='mpr.organizationalunit')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='budget_holder_roles', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'mpr_budget_holders',
                'ordering': ['-is_primary', 'user__first_name'],
            },
        ),
        migrations.CreateModel(
            name='BudgetSponsor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_primary', models.BooleanField(default=False, help_text='Primary budget sponsor for this unit')),
                ('approval_limit', models.DecimalField(blank=True, decimal_places=2, help_text='Maximum amount they can approve', max_digits=12, null=True)),
                ('sponsor_level', models.CharField(choices=[('level_1', 'Level 1 (up to 10k)'), ('level_2', 'Level 2 (up to 50k)'), ('level_3', 'Level 3 (up to 100k)'), ('executive', 'Executive (unlimited)')], default='level_1', max_length=50)),
                ('is_active', models.BooleanField(default=True)),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('assigned_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_budget_sponsors', to=settings.AUTH_USER_MODEL)),
                ('organizational_unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='budget_sponsors', to='mpr.organizationalunit')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='budget_sponsor_roles', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'mpr_budget_sponsors',
                'ordering': ['-is_primary', 'user__first_name'],
            },
        ),
        # Add new fields to OrganizationalUnit
        migrations.AddField(
            model_name='organizationalunit',
            name='primary_recruiter',
            field=models.ForeignKey(blank=True, help_text='Primary recruiter for this organizational unit', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='primary_recruiter_units', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='organizationalunit',
            name='primary_manager',
            field=models.ForeignKey(blank=True, help_text='Primary manager for this organizational unit', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='primary_manager_units', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='organizationalunit',
            name='primary_budget_holder',
            field=models.ForeignKey(blank=True, help_text='Primary budget holder for this organizational unit', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='primary_budget_holder_units', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='organizationalunit',
            name='primary_budget_sponsor',
            field=models.ForeignKey(blank=True, help_text='Primary budget sponsor for this organizational unit', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='primary_budget_sponsor_units', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='organizationalunit',
            name='cost_center',
            field=models.CharField(blank=True, help_text='Cost center code', max_length=50),
        ),
        migrations.AddField(
            model_name='organizationalunit',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='mpr.location'),
        ),
        migrations.AddField(
            model_name='organizationalunit',
            name='headcount_limit',
            field=models.IntegerField(blank=True, help_text='Maximum number of employees', null=True),
        ),
        migrations.AddField(
            model_name='organizationalunit',
            name='current_headcount',
            field=models.IntegerField(default=0, help_text='Current number of employees'),
        ),
        migrations.AddField(
            model_name='organizationalunit',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_org_units', to=settings.AUTH_USER_MODEL),
        ),
        # Add unique constraints
        migrations.AlterUniqueTogether(
            name='recruiter',
            unique_together={('user', 'organizational_unit')},
        ),
        migrations.AlterUniqueTogether(
            name='manager',
            unique_together={('user', 'organizational_unit')},
        ),
        migrations.AlterUniqueTogether(
            name='budgetholder',
            unique_together={('user', 'organizational_unit')},
        ),
        migrations.AlterUniqueTogether(
            name='budgetsponsor',
            unique_together={('user', 'organizational_unit')},
        ),
    ]