"""
Context extender module for edx-platform certificates
"""
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _

from nau_openedx_extensions.custom_registration_form.models import NauUserExtendedModel
from nau_openedx_extensions.edxapp_wrapper.grades import get_course_grades
from nau_openedx_extensions.edxapp_wrapper.registration import get_registration_extension_form

log = logging.getLogger(__name__)


def update_cert_context(context, user, course, **kwargs):
    """
    Updates certifcates context with custom data for the user within
    the course context
    """
    nau_cert_settings = course.cert_html_view_overrides.get('nau_certs_settings')

    update_context_with_custom_form(user, NauUserExtendedModel, context)
    if nau_cert_settings:
        update_context_with_grades(user, course, context, nau_cert_settings, kwargs['user_certificate'])
        update_context_with_interpolated_strings(context, nau_cert_settings, kwargs['certificate_language'])


def update_context_with_custom_form(user, custom_model, context):
    """
    Updates the context in-place with extra user information
    """
    custom_form = get_registration_extension_form()
    try:
        custom_model_instance = custom_model.objects.get(user=user)
    except ObjectDoesNotExist:
        # If a custom model does not exist for the user, just return
        return

    if custom_form:
        for field in custom_form.fields.keys():
            context_element = {
                field: getattr(custom_model_instance, field, '')
            }
            context.update(context_element)


def update_context_with_grades(user, course, context, settings, user_certificate):
    """
    Updates certifcates context with grades data for the user
    """
    # always add `user certificate` grade context
    context.update({
        'certificate_final_grade': user_certificate.grade,
    })

    if settings.get('calculate_grades_context', False):
        try:
            grades = get_course_grades(user, course)
            context_element = {
                'course_letter_grade': grades.letter_grade or '',
                'user_has_approved_course': grades.passed,
                'course_percent_grade': grades.percent,
            }
        except Exception:
            log.error(
                'Could not get grades for user %s in %s',
                user.username,
                course.display_name,
            )
        else:
            context.update(context_element)


def update_context_with_interpolated_strings(context, settings, certificate_language):
    """
    Updates certificate context using custom interpolated strings.
    Applies the corresponding translation before updating the context.
    """
    interpolated_strings = get_interpolated_strings(settings, certificate_language)

    if interpolated_strings:
        for key, value in interpolated_strings.iteritems():
            try:
                formatted_string = value.format(**context)
            except (ValueError, AttributeError, KeyError):
                log.error(
                    'Failed to add value (%s) as formatted string in the certificate context',
                    value,
                )
                continue
            else:
                # Finally, try to translate the string if defined in platform .po
                context.update({
                    key: _(formatted_string)
                })


def get_interpolated_strings(settings, certificate_language):
    """
    Returns a dict with custom interpolated strings available for a certificate language.
    Returns an empty dict if it cant find a string for the given language.
    """
    lang_interpolated_strings = {}
    multilang_interpolated_strings = settings.get('interpolated_strings')
    if multilang_interpolated_strings:
        for key, value in multilang_interpolated_strings.iteritems():
            for lang, string in value.iteritems():
                if lang in certificate_language:
                    lang_interpolated_strings[key] = string
                    break

    return lang_interpolated_strings