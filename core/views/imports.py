# Standard library
import re
import os
import csv
import json
import random
import calendar
import logging
from datetime import datetime, timedelta
from io import BytesIO
from collections import Counter
from email.mime.image import MIMEImage
from mimetypes import guess_type

# Third-party
import pandas as pd
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Border, Side

# Django core
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login, authenticate
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordResetView
from django.contrib.sites.models import Site
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.mail import send_mail, EmailMultiAlternatives, EmailMessage
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q, Prefetch, F, Case, When, IntegerField
from django.db.models.functions import TruncMonth
from django.http import FileResponse, JsonResponse, HttpResponse
from django.shortcuts import render, get_list_or_404, redirect, get_object_or_404
from django.template.loader import render_to_string          # ← was missing
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode
from django.utils.timezone import now
from django.views import View
from django.views.decorators.http import require_POST, require_http_methods
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# Local app imports
from core.models import FileCategory
from core.priority_rules import determine_priority
from core.signals import assign_director_permissions, assign_manager_permissions, assign_staff_permissions
from core.utils import can_user_access_file
from core.uttils.serializers import serialize_ticket, serialize_user_notification

from core.models import (
    ISSUE_MAPPING, ActivityLog, File, FileAccessLog, EscalationHistory,
    Customer, Region, Terminal, Unit, SystemUser, Zone, ProblemCategory,
    VersionControl, VersionComment, Report, Ticket, Profile, EmailOTP,
    TicketComment, UserNotification
)
from core.forms import (
    FilePasscodeForm, FileUploadForm, ProblemCategoryForm, TicketForm,
    EscalationNoteForm, UserUpdateForm, ProfileUpdateForm, TerminalForm,
    TerminalUploadForm, VersionControlForm, CustomUserCreationForm,
    LoginForm, OTPForm, TicketEditForm, TicketCommentForm
)

from core.utils import is_director, is_staff, is_manager, is_director_or_manager, can_user_access_file

logger = logging.getLogger(__name__)

from openpyxl import Workbook