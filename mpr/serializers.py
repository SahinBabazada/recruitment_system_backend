# mpr/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Job, OrganizationalUnit, Location, EmploymentType, HiringReason,
    Employee, TechnicalSkill, Language, Competency, ContractDuration,
    MPR, MPRComment, MPRStatusHistory
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['id', 'title', 'description', 'is_active']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class OrganizationalUnitSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    full_path = serializers.CharField(read_only=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationalUnit
        fields = [
            'id', 'name', 'type', 'parent', 'parent_name', 'code', 
            'description', 'is_active', 'full_path', 'children'
        ]

    def get_children(self, obj):
        if obj.children.exists():
            return OrganizationalUnitSerializer(obj.children.all(), many=True, context=self.context).data
        return []


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = [
            'id', 'name', 'address', 'city', 'country', 
            'location_type', 'is_active'
        ]


class EmploymentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmploymentType
        fields = ['id', 'name', 'description', 'is_active', 'is_default']


class HiringReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = HiringReason
        fields = ['id', 'name', 'description', 'is_active', 'is_default']


class EmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    position_title = serializers.CharField(source='position.title', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'employee_id', 'first_name', 'last_name', 'full_name',
            'email', 'department', 'department_name', 'position', 'position_title',
            'location', 'location_name', 'hire_date', 'is_active'
        ]


class TechnicalSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicalSkill
        fields = ['id', 'name', 'category', 'description', 'is_active']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ['id', 'name', 'code', 'is_active']


class CompetencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Competency
        fields = ['id', 'name', 'category', 'description', 'is_active']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ContractDurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDuration
        fields = ['id', 'name', 'months', 'description', 'is_active', 'is_default']


class MPRCommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = MPRComment
        fields = [
            'id', 'user', 'user_id', 'comment', 'is_internal',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class MPRStatusHistorySerializer(serializers.ModelSerializer):
    changed_by = UserSerializer(read_only=True)

    class Meta:
        model = MPRStatusHistory
        fields = [
            'id', 'from_status', 'to_status', 'changed_by',
            'changed_at', 'reason'
        ]
        read_only_fields = ['changed_at']


class MPRListSerializer(serializers.ModelSerializer):
    """Serializer for MPR list view with minimal data"""
    job_title = serializers.CharField(source='job_title.title', read_only=True)
    department = serializers.CharField(source='department.name', read_only=True)
    location = serializers.CharField(source='location.name', read_only=True)
    employment_type = serializers.CharField(source='employment_type.name', read_only=True)
    hiring_reason = serializers.CharField(source='hiring_reason.name', read_only=True)
    created_by = UserSerializer(read_only=True)
    applicant_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = MPR
        fields = [
            'id', 'mpr_number', 'status', 'priority', 'job_title',
            'department', 'location', 'employment_type', 'hiring_reason',
            'desired_start_date', 'created_by', 'created_at',
            'applicant_count'
        ]


class MPRDetailSerializer(serializers.ModelSerializer):
    """Serializer for MPR detail view with full data"""
    job_title = JobSerializer(read_only=True)
    job_title_id = serializers.IntegerField(write_only=True)
    
    department = OrganizationalUnitSerializer(read_only=True)
    department_id = serializers.IntegerField(write_only=True)
    
    division = OrganizationalUnitSerializer(read_only=True)
    division_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    unit = OrganizationalUnitSerializer(read_only=True)
    unit_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    location = LocationSerializer(read_only=True)
    location_id = serializers.IntegerField(write_only=True)
    
    employment_type = EmploymentTypeSerializer(read_only=True)
    employment_type_id = serializers.IntegerField(write_only=True)
    
    hiring_reason = HiringReasonSerializer(read_only=True)
    hiring_reason_id = serializers.IntegerField(write_only=True)
    
    replaced_employee = EmployeeSerializer(read_only=True)
    replaced_employee_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    technical_skills = TechnicalSkillSerializer(many=True, read_only=True)
    technical_skill_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    required_languages = LanguageSerializer(many=True, read_only=True)
    required_language_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    core_competencies = CompetencySerializer(many=True, read_only=True)
    core_competency_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    contract_duration = ContractDurationSerializer(read_only=True)
    contract_duration_id = serializers.IntegerField(write_only=True)
    
    recruiter = UserSerializer(read_only=True)
    recruiter_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    budget_holder = UserSerializer(read_only=True)
    budget_holder_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)
    rejected_by = UserSerializer(read_only=True)
    
    comments = MPRCommentSerializer(many=True, read_only=True)
    status_history = MPRStatusHistorySerializer(many=True, read_only=True)
    
    applicant_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = MPR
        fields = [
            'id', 'mpr_number', 'status', 'priority',
            
            # Position Information
            'job_title', 'job_title_id',
            'department', 'department_id',
            'division', 'division_id',
            'unit', 'unit_id',
            'location', 'location_id',
            'desired_start_date',
            'employment_type', 'employment_type_id',
            'hiring_reason', 'hiring_reason_id',
            'replaced_employee', 'replaced_employee_id',
            'business_justification',
            
            # Requirements
            'education_requirements',
            'technical_skills', 'technical_skill_ids',
            'required_languages', 'required_language_ids',
            'core_competencies', 'core_competency_ids',
            'assessment_requirements',
            'contract_duration', 'contract_duration_id',
            
            # Approval Information
            'recruiter', 'recruiter_id',
            'budget_holder', 'budget_holder_id',
            'proposed_candidate',
            
            # Audit Information
            'created_by', 'created_at', 'updated_at', 'updated_by',
            'approved_by', 'approved_at', 'rejected_by', 'rejected_at',
            'rejection_reason',
            
            # Related Data
            'comments', 'status_history', 'applicant_count'
        ]
        read_only_fields = [
            'mpr_number', 'created_at', 'updated_at', 'approved_at',
            'rejected_at', 'applicant_count'
        ]

    def create(self, validated_data):
        # Extract many-to-many field IDs
        technical_skill_ids = validated_data.pop('technical_skill_ids', [])
        required_language_ids = validated_data.pop('required_language_ids', [])
        core_competency_ids = validated_data.pop('core_competency_ids', [])
        
        # Set created_by
        validated_data['created_by'] = self.context['request'].user
        
        # Create MPR instance
        mpr = MPR.objects.create(**validated_data)
        
        # Set many-to-many relationships
        if technical_skill_ids:
            mpr.technical_skills.set(technical_skill_ids)
        if required_language_ids:
            mpr.required_languages.set(required_language_ids)
        if core_competency_ids:
            mpr.core_competencies.set(core_competency_ids)
        
        return mpr

    def update(self, instance, validated_data):
        # Extract many-to-many field IDs
        technical_skill_ids = validated_data.pop('technical_skill_ids', None)
        required_language_ids = validated_data.pop('required_language_ids', None)
        core_competency_ids = validated_data.pop('core_competency_ids', None)
        
        # Set updated_by
        validated_data['updated_by'] = self.context['request'].user
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update many-to-many relationships
        if technical_skill_ids is not None:
            instance.technical_skills.set(technical_skill_ids)
        if required_language_ids is not None:
            instance.required_languages.set(required_language_ids)
        if core_competency_ids is not None:
            instance.core_competencies.set(core_competency_ids)
        
        return instance

    def validate(self, data):
        """Validate MPR data"""
        # Validate organizational hierarchy
        department_id = data.get('department_id')
        division_id = data.get('division_id')
        unit_id = data.get('unit_id')
        
        if division_id and department_id:
            try:
                division = OrganizationalUnit.objects.get(id=division_id)
                if division.parent_id != department_id:
                    raise serializers.ValidationError(
                        "Division must belong to the selected department"
                    )
            except OrganizationalUnit.DoesNotExist:
                raise serializers.ValidationError("Invalid division selected")
        
        if unit_id and (department_id or division_id):
            try:
                unit = OrganizationalUnit.objects.get(id=unit_id)
                valid_parents = [department_id]
                if division_id:
                    valid_parents.append(division_id)
                
                if unit.parent_id not in valid_parents:
                    raise serializers.ValidationError(
                        "Unit must belong to the selected department or division"
                    )
            except OrganizationalUnit.DoesNotExist:
                raise serializers.ValidationError("Invalid unit selected")
        
        return data


class MPRCreateSerializer(MPRDetailSerializer):
    """Serializer for creating MPR with required fields validation"""
    
    class Meta(MPRDetailSerializer.Meta):
        pass

    def validate(self, data):
        data = super().validate(data)
        
        # Additional validation for creation
        required_fields = [
            'job_title_id', 'department_id', 'location_id',
            'desired_start_date', 'employment_type_id', 'hiring_reason_id',
            'education_requirements', 'contract_duration_id'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not data.get(field):
                missing_fields.append(field.replace('_id', '').replace('_', ' ').title())
        
        if missing_fields:
            raise serializers.ValidationError(
                f"The following fields are required: {', '.join(missing_fields)}"
            )
        
        return data


class MPRApprovalSerializer(serializers.Serializer):
    """Serializer for MPR approval/rejection actions"""
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data['action'] == 'reject' and not data.get('reason'):
            raise serializers.ValidationError(
                "Reason is required when rejecting an MPR"
            )
        return data