import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from django.core.exceptions import ValidationError
from django.core.management import BaseCommand, call_command
from django.core.management.base import CommandError, SystemCheckError
from django.core.validators import validate_email
from strategy_field.utils import fqn

from bitcaster.config import env
from bitcaster.dispatchers import EmailDispatcher
from bitcaster.models import Channel

if TYPE_CHECKING:
    from argparse import ArgumentParser

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    requires_migrations_checks = False
    requires_system_checks = []

    def add_arguments(self, parser: "ArgumentParser") -> None:
        parser.add_argument(
            "--with-check",
            action="store_true",
            dest="check",
            default=False,
            help="Run checks",
        )
        parser.add_argument(
            "--no-check",
            action="store_false",
            dest="check",
            default=False,
            help="Do not run checks",
        )
        parser.add_argument(
            "--no-migrate",
            action="store_false",
            dest="migrate",
            default=True,
            help="Do not run migrations",
        )
        parser.add_argument(
            "--prompt",
            action="store_true",
            dest="prompt",
            default=False,
            help="Let ask for confirmation",
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            dest="debug",
            default=False,
            help="debug mode",
        )
        parser.add_argument(
            "--no-static",
            action="store_false",
            dest="static",
            default=True,
            help="Do not run collectstatic",
        )

        parser.add_argument(
            "--admin-email",
            action="store",
            dest="admin_email",
            default="",
            help="Admin email",
        )
        parser.add_argument(
            "--admin-password",
            action="store",
            dest="admin_password",
            default="",
            help="Admin password",
        )

    def get_options(self, options: dict[str, Any]) -> None:
        self.verbosity = options["verbosity"]
        self.run_check = options["check"]
        self.prompt = not options["prompt"]
        self.static = options["static"]
        self.migrate = options["migrate"]
        self.debug = options["debug"]

        self.admin_email = str(options["admin_email"] or env("ADMIN_EMAIL", ""))
        self.admin_password = str(options["admin_password"] or env("ADMIN_PASSWORD", ""))

    def halt(self, e: Exception) -> None:  # pragma: no cover
        self.stdout.write(str(e), style_func=self.style.ERROR)
        self.stdout.write("\n\n***", style_func=self.style.ERROR)
        self.stdout.write("SYSTEM HALTED", style_func=self.style.ERROR)
        self.stdout.write("Unable to start...", style_func=self.style.ERROR)
        if self.debug:
            raise e

        sys.exit(1)

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: C901
        from bitcaster.models import Application, Event, Message, Organization, Project, User

        bitcaster: Optional[Application] = None
        admin: Optional[User] = None

        self.get_options(options)
        if self.verbosity >= 1:
            echo = self.stdout.write
        else:
            echo = lambda *a, **kw: None  # noqa: E731

        try:
            extra = {
                "no_input": not self.prompt,
                "verbosity": self.verbosity - 1,
                "stdout": self.stdout,
            }
            echo("Running upgrade", style_func=self.style.WARNING)
            call_command("env", check=True)

            if self.run_check:
                call_command("check", deploy=True, verbosity=self.verbosity - 1)
            if self.static:
                static_root = Path(env("STATIC_ROOT"))
                echo(f"Run collectstatic to: '{static_root}' - '{static_root.absolute()}")
                if not static_root.exists():
                    static_root.mkdir(parents=True)
                call_command("collectstatic", **extra)

            if self.migrate:
                echo("Run migrations")
                call_command("migrate", **extra)
                call_command("create_extra_permissions")

            echo("Remove stale contenttypes")
            call_command("remove_stale_contenttypes", **extra)
            if self.admin_email:
                if User.objects.filter(email=self.admin_email).exists():
                    echo(
                        f"User {self.admin_email} found, skip creation",
                        style_func=self.style.WARNING,
                    )
                else:
                    echo(f"Creating superuser: {self.admin_email}", style_func=self.style.WARNING)
                    validate_email(self.admin_email)
                    os.environ["DJANGO_SUPERUSER_USERNAME"] = self.admin_email
                    os.environ["DJANGO_SUPERUSER_EMAIL"] = self.admin_email
                    os.environ["DJANGO_SUPERUSER_PASSWORD"] = self.admin_password
                    call_command(
                        "createsuperuser",
                        email=self.admin_email,
                        username=self.admin_email,
                        verbosity=self.verbosity - 1,
                        interactive=False,
                    )
                admin: "User" = User.objects.get(email=self.admin_email)
                os4d = Organization.objects.get_or_create(name="OS4D", owner=admin)[0]
                echo("Creating initial structure")
                prj = Project.objects.get_or_create(name="Bitcaster", organization=os4d, owner=os4d.owner)[0]
                bitcaster = Application.objects.get_or_create(name="Bitcaster", project=prj, owner=os4d.owner)[0]
            if not bitcaster:
                bitcaster = Application.objects.get(
                    name="Bitcaster", project__name="Bitcaster", project__organization__name="OS4D"
                )[0]
            from bitcaster.dispatchers.log import BitcasterLogDispatcher

            ch_log = Channel.objects.get_or_create(
                name="BitcasterLog",
                organization=bitcaster.project.organization,
                project=bitcaster.project,
                application=bitcaster,
                dispatcher=fqn(BitcasterLogDispatcher),
            )[0]
            ch_mail = Channel.objects.get_or_create(
                name=Channel.SYSTEM_EMAIL_CHANNEL_NAME,
                organization=bitcaster.project.organization,
                project=bitcaster.project,
                application=bitcaster,
                dispatcher=fqn(EmailDispatcher),
            )[0]
            for event_name in ["application_locked", "application_unlocked"]:
                ev: "Event" = bitcaster.register_event(event_name)
                ev.channels.add(ch_mail)
                ev.channels.add(ch_log)
                Message.objects.get_or_create(
                    event=ev,
                    name="Message for {event_name}".format(event_name=event_name),
                    code="message-{}".format(event_name),
                    subject="{{subject}}",
                    content="{{message}}",
                    html_content="{{message}}",
                )
            if admin:
                echo(f"Creating address: {self.admin_email}", style_func=self.style.WARNING)
                admin_email = admin.addresses.get_or_create(name="email", value=self.admin_email)[0]
                admin_email.validate_channel(ch_mail)

            echo("Upgrade completed", style_func=self.style.SUCCESS)
        except ValidationError as e:
            self.halt(Exception("\n- ".join(["Wrong argument(s):", *e.messages])))
        except (CommandError, SystemCheckError) as e:
            self.halt(e)
        except Exception as e:
            self.stdout.write(str(e), style_func=self.style.ERROR)
            logger.exception(e)
            self.halt(e)
