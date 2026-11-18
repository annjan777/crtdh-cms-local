"""factory_boy factories for CMS users with contract roles (§3: groups editor/publisher/admin)."""
import factory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.accounts.roles import ADMIN, EDITOR, ORDER, PUBLISHER

# Local test value only (contract §7). Never a real password.
TEST_PASSWORD = "test-pass-Q9!local"


def ensure_role_groups():
    return {name: Group.objects.get_or_create(name=name)[0] for name in ORDER}


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
        django_get_or_create = ("username",)
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.test")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True
    password = factory.PostGenerationMethodCall("set_password", TEST_PASSWORD)

    @factory.post_generation
    def role(self, create, extracted, **kwargs):
        """UserFactory(role="publisher") puts the user in that group (one group; roles.py derives the rest)."""
        if extracted:
            groups = ensure_role_groups()
            self.groups.add(groups[extracted])
        if create:
            self.save()


class EditorFactory(UserFactory):
    username = factory.Sequence(lambda n: f"editor{n}")
    role = EDITOR


class PublisherFactory(UserFactory):
    username = factory.Sequence(lambda n: f"publisher{n}")
    role = PUBLISHER


class AdminRoleFactory(UserFactory):
    username = factory.Sequence(lambda n: f"cmsadmin{n}")
    role = ADMIN


def make_user(role=None, **kw):
    """role in {None, "editor", "publisher", "admin", "superuser"}; None = authenticated, no CMS role."""
    if role == "superuser":
        return UserFactory(is_superuser=True, is_staff=True, **kw)
    return UserFactory(role=role, **kw)
