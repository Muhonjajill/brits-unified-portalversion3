from .imports import *

def in_group(user, group_name):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name=group_name).exists())
    
def is_director(user):
    return in_group(user, 'Director')
    
def is_manager(user):
    return in_group(user, 'Manager')

def is_director_or_manager(user):
    return is_director(user) or is_manager(user)
    
def is_staff(user):
    return in_group(user, 'Staff')

class CustomPasswordResetView(PasswordResetView):
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    template_name = 'accounts/password_reset_form.html'

    def get_email_context(self, **kwargs):
        context = super().get_email_context(**kwargs)
        context['site_name'] = getattr(settings, 'SITE_NAME', 'My Site')
        context['domain'] = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
        context['protocol'] = getattr(settings, 'SITE_PROTOCOL', 'http')
        return context

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    class Meta:
        model = User
        fields = ['username', 'email', 'password']

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            print(f"User {user.username} created successfully.")

            superuser = User.objects.filter(is_superuser=True).first()  
            
            if superuser:
                subject = 'New User Registration - Assign Role'
                message = render_to_string('email/new_user_email.html', {'user': user})
                email = EmailMessage(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [superuser.email],
                )
                email.content_subtype = "html"  
                email.send()

            return redirect('login')
        else:
            print(f"Form errors: {form.errors}")
    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/register.html', {'form': form})



def login_view(request):
    form = LoginForm()

    if request.method == 'POST':
        form = LoginForm(request.POST)
        
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)
            if user is not None:
                user_roles = list(user.groups.values_list('name', flat=True))
                allowed_roles = ['Director', 'Manager', 'Staff', 'Customer'] 

                if not user.is_superuser and not any(role in allowed_roles for role in user_roles):
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Your account has not been issued a role yet. Kindly be patient for a while as we handle that. Thank you!'
                    })
                request.session['pre_otp_user'] = user.id 
                otp = str(random.randint(100000, 999999))
                EmailOTP.objects.update_or_create(user=user, defaults={'otp': otp, 'created_at': timezone.now()})
                
                # Prepare HTML and plain text content
                subject = 'Your OTP Code'
                html_content = render_to_string('email/otp_email.html', {
                    'username': user.username,
                    'otp': otp,
                })
                text_content = strip_tags(html_content)

                # Create the email object
                email = EmailMultiAlternatives(
                    subject,
                    text_content,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                )
                email.attach_alternative(html_content, "text/html")

                # Attach the logo as an inline image using MIMEImage
                
                with open(str(settings.BASE_DIR / "static/icons/logo.png"), "rb") as logo_file:
                    logo_data = logo_file.read()
                    logo = MIMEImage(logo_data, name='logo.png')
                    logo.add_header('Content-ID', '<logo>')  

                    email.attach(logo) 
                
                print("Generated otp:", otp)

                email.send()
                return JsonResponse({'status': 'otp_sent'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid username or password'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid form input'})
    return render(request, 'accounts/login.html', {'form': form})


def verify_otp_view(request):
    user_id = request.session.get('pre_otp_user')
    if not user_id:
        return JsonResponse({'status': 'error', 'message': 'Session expired. Please login again.'})

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'})

    if request.method == "POST":
        form = OTPForm(request.POST)
        if form.is_valid():
            otp_input = form.cleaned_data["otp"]
            otp_instance = EmailOTP.objects.filter(user=user).first()

            if otp_instance:
                if otp_input != otp_instance.otp:
                    return JsonResponse({'status': 'error', 'message': 'Invalid OTP'})
                elif otp_instance.is_expired():
                    return JsonResponse({'status': 'error', 'message': 'Expired OTP'})
                else:
                    auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    if 'pre_otp_user' in request.session:
                        del request.session['pre_otp_user']
                    otp_instance.delete()  
                    return JsonResponse({'status': 'verified', 'redirect_url': '/pre_dashboards/'})
            else:
                return JsonResponse({'status': 'error', 'message': 'OTP not found'})

        return JsonResponse({'status': 'error', 'message': 'Invalid OTP input'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})



# Email notification functions
def send_inhouse_user_email(request, user, password, role):
    """Send welcome email to in-house users"""
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    reset_url = request.build_absolute_uri(
        reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
    )
    
    context = {
        'user': user,
        'password': password,
        'role': role,
        'user_type': 'In-house',
        'reset_url': reset_url,
        'site_url': getattr(settings, 'SITE_URL', 'localhost'),
    }
    
    subject = f"Welcome to BRITS Ticketing System - {role} Account Created"
    message = render_to_string('email/inhouse_user_created.html', context)
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], html_message=message)


def send_overseer_email(request, user, password, customer):
    """Send welcome email to overseer"""
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    reset_url = request.build_absolute_uri(
        reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
    )
    
    context = {
        'user': user,
        'password': password,
        'role': 'Overseer',
        'user_type': 'Customer',
        'customer': customer,
        'reset_url': reset_url,
        'site_url': getattr(settings, 'SITE_URL', 'localhost'),
    }
    
    subject = f"Welcome to BRITS Ticketing System - Overseer Account for {customer.name}"
    message = render_to_string('email/overseer_created.html', context)
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], html_message=message)


def send_custodian_email(request, user, password, customer, terminal):
    """Send welcome email to custodian"""
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    reset_url = request.build_absolute_uri(
        reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
    )
    
    context = {
        'user': user,
        'password': password,
        'role': 'Custodian',
        'user_type': 'Customer',
        'customer': customer,
        'terminal': terminal,
        'reset_url': reset_url,
        'site_url': getattr(settings, 'SITE_URL', 'localhost'),
    }
    
    subject = f"Welcome to BRITS Ticketing System - Custodian Account for {customer.name} - {terminal.branch_name}"
    message = render_to_string('email/custodian_created.html', context)
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], html_message=message)


def send_role_assigned_email(user, new_role, request, customer=None, terminal=None):
    """Send role assignment notification email"""
    subject = f"Your Role Has Been Updated: {new_role}"

    customer_name = None
    terminal_name = None

    if new_role == 'Overseer' and customer:
        customer_name = customer.name
    elif new_role == 'Custodian' and terminal:
        terminal_name = terminal.branch_name
        customer_name = terminal.customer.name if terminal.customer else None

    # Fallback if not provided
    if not customer_name and new_role == 'Overseer':
        customer_obj = Customer.objects.filter(overseer=user).first()
        if customer_obj:
            customer_name = customer_obj.name

    if not terminal_name and new_role == 'Custodian':
        terminal_obj = Terminal.objects.filter(custodian=user).first()
        if terminal_obj:
            terminal_name = terminal_obj.branch_name
            customer_name = terminal_obj.customer.name if terminal_obj.customer else None

    try:
        domain = getattr(settings, 'SITE_URL', 'localhost')
    except:
        domain = 'localhost'

    message = render_to_string('email/role_assigned_notification.html', {
        'user': user,
        'new_role': new_role,
        'customer_name': customer_name,
        'terminal_name': terminal_name,
        'domain': domain,
    })

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,  
            [user.email],  
            html_message=message 
        )
    except Exception as e:
        messages.error(request, "There was an error sending the email.")


def send_role_removed_email(user, role, request):
    """Send role removal notification email"""
    subject = f"Your Role Has Been Removed: {role}"

    if role == 'Overseer':
        role_message = "You have been removed as the overseer for the customer."
    elif role == 'Custodian':
        role_message = "You have been removed as the custodian for the terminal."
    else:
        role_message = f"Your role as {role} has been removed."

    try:
        message = render_to_string('email/role_removed_notification.html', {
            'user': user,
            'role_message': role_message,
        })

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=message
        )
    except Exception as e:
        messages.error(request, "There was an error sending the email.")


def send_user_updated_email(request, user, changes, new_role, profile):
    """Send email notification when user details are updated"""
    subject = "Your Account Has Been Updated - BRITS Ticketing System"
    
    customer_name = None
    terminal_name = None
    
    if profile.customer:
        customer_name = profile.customer.name
    if profile.terminal:
        terminal_name = profile.terminal.branch_name
    
    context = {
        'user': user,
        'changes': changes,
        'new_role': new_role,
        'customer_name': customer_name,
        'terminal_name': terminal_name,
        'site_url': getattr(settings, 'SITE_URL', 'localhost'),
    }
    
    message = render_to_string('email/user_updated_notification.html', context)
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=message
        )
    except Exception as e:
        messages.error(request, "There was an error sending the update notification email.")