from django.conf import settings
from django.core.checks import register, Tags, Warning
from .middleware import ContentSecurityPolicyMiddleware

@register(Tags.security, deploy=True)
def csp_configuration_check(app_configs, **kwargs):
    errors = []
    csp_settings = ContentSecurityPolicyMiddleware.get_csp_settings(settings)
    if not ContentSecurityPolicyMiddleware.find_policy(csp_settings):
        errors.append(
            Warning(
                'No Content Security Policy (CSP) is configured.',
                hint='Check the main project settings module for configuration documentation under CONTENT_SECURITY_POLICY',
                id='tunnistamo.W001'
            )
        )
    elif csp_settings.get('report_only') is True:
        errors.append(
            Warning(
                'The Content Security Policy (CSP) is only reported, not enforced.',
                hint='Check the main project settings module for configuration documentation under CONTENT_SECURITY_POLICY[\'report_only\']',
                id='tunnistamo.W002'
            )
        )
    return errors
