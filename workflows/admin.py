from django.contrib import admin
from workflows.models import State
from workflows.models import StateInheritanceBlock
from workflows.models import StatePermissionRelation
from workflows.models import StateObjectRelation
from workflows.models import Transition
from workflows.models import Workflow
from workflows.models import WorkflowObjectRelation
from workflows.models import WorkflowModelRelation
from workflows.models import WorkflowPermissionRelation


class StateInline(admin.TabularInline):
    model = State


class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('name', 'codename', 'initial_state')
    inlines = [
        StateInline,
    ]

admin.site.register(Workflow, WorkflowAdmin)


class StatePermissionRelationInline(admin.TabularInline):
    model = StatePermissionRelation
    ordering = ('state', 'permission', 'role')


class StateAdmin(admin.ModelAdmin):
    list_display = ('name', 'codename', 'workflow')
    list_filter = ('workflow',)
    ordering = ('codename',)
    inlines = [StatePermissionRelationInline]

admin.site.register(State, StateAdmin)


admin.site.register(StateInheritanceBlock)


class StateObjectRelationAdmin(admin.ModelAdmin):
    list_display = ('content_type', 'content_id', 'state', 'update_date')
    list_filter = ('state','content_type')
    search_fields = ('content_id',)

admin.site.register(StateObjectRelation, StateObjectRelationAdmin)


class StatePermissionRelationAdmin(admin.ModelAdmin):
    list_display = ('state', 'permission', 'role')
    list_filter = ('state', 'permission', 'role')
    ordering = ('state', 'permission', 'role')

admin.site.register(StatePermissionRelation, StatePermissionRelationAdmin)


admin.site.register(Transition)
admin.site.register(WorkflowObjectRelation)
admin.site.register(WorkflowModelRelation)
admin.site.register(WorkflowPermissionRelation)

