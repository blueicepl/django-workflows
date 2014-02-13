# -*- coding: utf-8 -*-
from django.conf import settings
from appconf import AppConf


class WorkflowConf(AppConf):
    ENABLE_STATE_HISTORY = False
