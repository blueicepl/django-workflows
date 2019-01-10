from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models

# django imports
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

# permissions imports
import permissions.utils
from permissions.models import Permission
from permissions.models import Role


class WorkflowManager(models.Manager):

    def get_by_natural_key(self, codename):
        return self.get(codename=codename)


class Workflow(models.Model):
    """A workflow consists of a sequence of connected (through transitions)
    states. It can be assigned to a model and / or model instances. If a
    model instance has a workflow it takes precendence over the model's
    class workflow

    **Attributes:**

    model
        The model the workflow belongs to. Can be any

    content
        The object the workflow belongs to.

    name
        The unique name of the workflow.

    states
        The states of the workflow.

    initial_state
        The initial state the model / content gets if created.

    """
    name = models.CharField(_("Name"), max_length=100, unique=True)
    codename = models.CharField(_("Codename"), max_length=100, unique=True)
    initial_state = models.ForeignKey("State", related_name="workflow_state", blank=True, null=True)
    permissions = models.ManyToManyField(Permission, symmetrical=False, through="WorkflowPermissionRelation")

    objects = WorkflowManager()

    def __unicode__(self):
        return self.name

    def get_initial_state(self):
        """Returns the initial state of the workflow. Takes the first one if
        no initial state had been defined.
        """
        if self.initial_state:
            return self.initial_state
        else:
            try:
                return self.states.all()[0]
            except IndexError:
                return None

    def get_objects(self):
        """Returns all objects which have this workflow assigned. Globally
        (via the object's content type) or locally (via the object itself).
        """
        import workflows.utils
        objs = []

        # Get all objects whose content type has this workflow
        for wmr in WorkflowModelRelation.objects.filter(workflow=self):
            ctype = wmr.content_type
            # We have also to check whether the global workflow is not
            # overwritten.
            for obj in ctype.model_class().objects.all():
                if workflows.utils.get_workflow(obj) == self:
                    objs.append(obj)

        # Get all objects whose local workflow this workflow
        for wor in WorkflowObjectRelation.objects.filter(workflow=self):
            if wor.content not in objs:
                objs.append(wor.content)

        return objs

    def set_to(self, ctype_or_obj):
        """Sets the workflow to provided content type or object. See the specific
        methods for more information.

        **Parameters:**

        ctype_or_obj
            The content type or the object to which the workflow should be set.
            Can be either a ContentType instance or any Django model instance.
        """
        if isinstance(ctype_or_obj, ContentType):
            return self.set_to_model(ctype_or_obj)
        else:
            return self.set_to_object(ctype_or_obj)

    def set_to_model(self, ctype):
        """Sets the workflow to the passed content type. If the content
        type has already an assigned workflow the workflow is overwritten.

        **Parameters:**

        ctype
            The content type which gets the workflow. Can be any Django model
            instance.
        """
        try:
            wor = WorkflowModelRelation.objects.get(content_type=ctype)
        except WorkflowModelRelation.DoesNotExist:
            WorkflowModelRelation.objects.create(content_type=ctype, workflow=self)
        else:
            wor.workflow = self
            wor.save()

    def set_to_object(self, obj):
        """Sets the workflow to the passed object.

        If the object has already the given workflow nothing happens. Otherwise
        the workflow is set to the object state is set to the workflow's
        initial state.

        **Parameters:**

        obj
            The object which gets the workflow.
        """
        import workflows.utils

        ctype = ContentType.objects.get_for_model(obj)
        try:
            wor = WorkflowObjectRelation.objects.get(content_type=ctype, content_id=obj.id)
        except WorkflowObjectRelation.DoesNotExist:
            WorkflowObjectRelation.objects.create(content=obj, workflow=self)
            workflows.utils.set_state(obj, self.initial_state)
        else:
            if wor.workflow != self:
                wor.workflow = self
                wor.save()
                workflows.utils.set_state(obj, self.initial_state)

    def natural_key(self):
        return self.codename,


class StateManager(models.Manager):

    def get_by_natural_key(self, codename):
        return self.get(codename=codename)


class State(models.Model):
    """A certain state within workflow.

    **Attributes:**

    name
        The unique name of the state within the workflow.

    workflow
        The workflow to which the state belongs.

    transitions
        The transitions of a workflow state.

    """
    name = models.CharField(_("Name"), max_length=100)
    codename = models.CharField(_("Codename"), max_length=100, unique=True)
    workflow = models.ForeignKey(Workflow, verbose_name=_("Workflow"), related_name="states")
    transitions = models.ManyToManyField("Transition", verbose_name=_("Transitions"), blank=True, related_name="states")

    objects = StateManager()

    class Meta:
        ordering = ("name", )

    def __unicode__(self):
        return u"%s (%s)" % (self.name, self.workflow.name)

    def get_allowed_transitions(self, obj, user):
        """Returns all allowed transitions for passed object and user.
        """
        def _condition_met():
            if transition.condition:
                # noinspection PyBroadException
                try:
                    return bool(eval(transition.condition, {
                        'obj': obj,
                        'user': user,
                        'transition': transition
                    }))
                except Exception:
                    return False
            return True

        transitions = []
        for transition in self.transitions.all():
            permission = transition.permission
            if permission is None:
                if _condition_met():
                    transitions.append(transition)
            else:
                # First we try to get the objects specific has_permission
                # method (in case the object inherits from the PermissionBase
                # class).
                try:
                    if obj.has_permission(user, permission.codename) and _condition_met():
                        transitions.append(transition)
                except AttributeError:
                    if permissions.utils.has_permission(obj, user, permission.codename) and _condition_met():
                        transitions.append(transition)
        return transitions

    def natural_key(self):
        return self.codename,


class TransitionManager(models.Manager):

    def get_by_natural_key(self, codename):
        return self.get(codename=codename)


class Transition(models.Model):
    """A transition from a source to a destination state. The transition can
    be used from several source states.

    **Attributes:**

    name
        The unique name of the transition within a workflow.

    workflow
        The workflow to which the transition belongs. Must be a Workflow
        instance.

    destination
        The state after a transition has been processed. Must be a State
        instance.

    condition
        The condition when the transition is available. Can be any python
        expression.

    permission
        The necessary permission to process the transition. Must be a
        Permission instance.

    """
    name = models.CharField(_("Name"), max_length=100)
    codename = models.CharField(_("Codename"), max_length=100, unique=True)
    workflow = models.ForeignKey(Workflow, verbose_name=_("Workflow"), related_name="transitions")
    destination = models.ForeignKey(State, verbose_name=_("Destination"), null=True, blank=True,
                                    related_name="destination_state")
    condition = models.TextField(_("Condition"), blank=True)
    permission = models.ForeignKey(Permission, verbose_name=_("Permission"), blank=True, null=True)

    objects = TransitionManager()

    def __unicode__(self):
        return u"%s (%s)" % (self.name, self.workflow.name)

    def natural_key(self):
        return self.codename,


class StateObjectRelation(models.Model):
    """Stores the workflow state of an object.

    Provides a way to give any object a workflow state without changing the
    object's model.

    **Attributes:**

    content
        The object for which the state is stored. This can be any instance of
        a Django model.

    state
        The state of content. This must be a State instance.
    """
    content_type = models.ForeignKey(ContentType, verbose_name=_("Content type"), related_name="state_object",
                                     blank=True, null=True)
    content_id = models.PositiveIntegerField(_("Content id"), blank=True, null=True)
    content = GenericForeignKey(ct_field="content_type", fk_field="content_id")
    state = models.ForeignKey(State, verbose_name=_("State"))
    update_date = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u"%s %s - %s" % (self.content_type.name, self.content_id, self.state.name)

    class Meta:
        unique_together = ("content_type", "content_id", "state")


class StateObjectHistory(models.Model):
    """Stores the workflow state history of an object.

    Provides a way to give any object a workflow state history without changing the
    object's model.

    **Attributes:**

    content
        The object for which the state is stored. This can be any instance of
        a Django model.

    state
        The state of content. This must be a State instance.
    """
    content_type = models.ForeignKey(ContentType, verbose_name=_("Content type"), related_name="state_history",
                                     blank=True, null=True)
    content_id = models.PositiveIntegerField(_("Content id"), blank=True, null=True)
    content = GenericForeignKey(ct_field="content_type", fk_field="content_id")
    state = models.ForeignKey(State, verbose_name=_("State"))
    update_date = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return u"%s %s - %s" % (self.content_type.name, self.content_id, self.state.name)


class WorkflowObjectRelation(models.Model):
    """Stores an workflow of an object.

    Provides a way to give any object a workflow without changing the object's
    model.

    **Attributes:**

    content
        The object for which the workflow is stored. This can be any instance of
        a Django model.

    workflow
        The workflow which is assigned to an object. This needs to be a workflow
        instance.
    """
    content_type = models.ForeignKey(ContentType, verbose_name=_("Content type"), related_name="workflow_object",
                                     blank=True, null=True)
    content_id = models.PositiveIntegerField(_("Content id"), blank=True, null=True)
    content = GenericForeignKey(ct_field="content_type", fk_field="content_id")
    workflow = models.ForeignKey(Workflow, verbose_name=_("Workflow"), related_name="wors")

    class Meta:
        unique_together = ("content_type", "content_id")

    def __unicode__(self):
        return u"%s %s - %s" % (self.content_type.name, self.content_id, self.workflow.name)


class WorkflowModelRelation(models.Model):
    """Stores an workflow for a model (ContentType).

    Provides a way to give any object a workflow without changing the model.

    **Attributes:**

    Content Type
        The content type for which the workflow is stored. This can be any
        instance of a Django model.

    workflow
        The workflow which is assigned to an object. This needs to be a
        workflow instance.
    """
    workflow = models.ForeignKey(Workflow, verbose_name=_("Workflow"), related_name="wmrs")
    content_type = models.ForeignKey(ContentType, verbose_name=_("Content Type"), unique=True)

    def __unicode__(self):
        return u"%s - %s" % (self.content_type.name, self.workflow.name)

    def natural_key(self):
        return self.workflow, self.content_type

    class Meta:
        unique_together = ("workflow", "content_type")


# Permissions relation #######################################################


class WorkflowPermissionRelation(models.Model):
    """Stores the permissions for which a workflow is responsible.

    **Attributes:**

    workflow
        The workflow which is responsible for the permissions. Needs to be a
        Workflow instance.

    permission
        The permission for which the workflow is responsible. Needs to be a
        Permission instance.
    """
    workflow = models.ForeignKey(Workflow)
    permission = models.ForeignKey(Permission, related_name="permissions")

    class Meta:
        unique_together = ("workflow", "permission")

    def __unicode__(self):
        return u"%s %s" % (self.workflow.name, self.permission.name)

    def natural_key(self):
        return self.workflow, self.permission


class StateInheritanceBlock(models.Model):
    """Stores inheritance block for state and permission.

    **Attributes:**

    state
        The state for which the inheritance is blocked. Needs to be a State
        instance.

    permission
        The permission for which the instance is blocked. Needs to be a
        Permission instance.
    """
    state = models.ForeignKey(State, verbose_name=_("State"))
    permission = models.ForeignKey(Permission, verbose_name=_("Permission"))

    def __unicode__(self):
        return u"%s %s" % (self.state.name, self.permission.name)


class StatePermissionManager(models.Manager):

    def get_by_natural_key(self, state, role, permission):
        return self.get(state=state, role=role, permission=permission)


class StatePermissionRelation(models.Model):
    """Stores granted permission for state and role.

    **Attributes:**

    state
        The state for which the role has the permission. Needs to be a State
        instance.

    permission
        The permission for which the workflow is responsible. Needs to be a
        Permission instance.

    role
        The role for which the state has the permission. Needs to be a lfc
        Role instance.
    """
    state = models.ForeignKey(State, verbose_name=_("State"))
    permission = models.ForeignKey(Permission, verbose_name=_("Permission"))
    role = models.ForeignKey(Role, verbose_name=_("Role"))

    objects = StatePermissionManager()

    def __unicode__(self):
        return u"%s %s %s" % (self.state.name, self.role.name, self.permission.name)

    def natural_key(self):
        return self.state, self.role, self.permission

    class Meta:
        verbose_name = _("State Permission Relation")
        verbose_name_plural = _("States Permissions Relations")
        unique_together = ('state', 'permission', 'role')

