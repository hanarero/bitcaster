from bitcaster.social.models import SocialProvider, Provider
from testutils.factories.social import SocialProviderFactory


def test_manager(db):
    SocialProviderFactory(provider=Provider.GITHUB)
    SocialProviderFactory(provider=Provider.GOOGLE_OAUTH2)
    SocialProviderFactory(provider=Provider.AZUREAD_TENANT_OAUTH2)

    assert SocialProvider.objects.choices() == [
        ("github", "Github"),
        ("google-oauth2", "Google"),
        ("azuread-tenant-oauth2", "Azure Tenant"),
    ]
