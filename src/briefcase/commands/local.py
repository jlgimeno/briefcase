import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from briefcase.config import BaseConfig
from briefcase.exceptions import BriefcaseCommandError

from .base import BaseCommand
from .create import DependencyInstallError, write_dist_info


class LocalCommand(BaseCommand):
    cmd_line = 'briefcase local'
    command = 'local'
    output_format = None
    description = 'Run a briefcase project in the local environment'

    @property
    def platform(self):
        """The local command always reports as the local platform."""
        return {
            'darwin': 'macOS',
            'linux': 'linux',
            'win32': 'windows',
        }[sys.platform]

    def bundle_path(self, app):
        "A placeholder; Local command doesn't have a bundle path"
        raise NotImplementedError()

    def binary_path(self, app):
        "A placeholder; Local command doesn't have a binary path"
        raise NotImplementedError()

    def distribution_path(self, app):
        "A placeholder; Local command doesn't have a distribution path"
        raise NotImplementedError()

    def add_options(self, parser):
        parser.add_argument(
            '-a',
            '--app',
            dest='appname',
            help='The app to run'
        )
        parser.add_argument(
            '-d',
            '--update_dependencies',
            action="store_true",
            help='Update dependencies for app'
        )

    def install_local_dependencies(self, app: BaseConfig, **kwargs):
        """
        Install the dependencies for the app locally.

        :param app: The config object for the app
        """
        if app.requires:
            try:
                self.subprocess.run(
                    [
                        sys.executable, "-m",
                        "pip", "install",
                        "--upgrade",
                    ] + app.requires,
                    check=True,
                )
            except subprocess.CalledProcessError:
                raise DependencyInstallError()
        else:
            print("No application dependencies.")

    def run_local_app(self, app: BaseConfig, **kwargs):
        """
        Run the app in the local environment.

        :param app: The config object for the app
        """
        try:
            # Create a shell environment where PYTHONPATH points to the source
            # directories described by the app config.
            env = os.environ.copy()
            env['PYTHONPATH'] = ':'.join(
                app.rsplit('/', 1)[0]
                for app in app.sources
            )

            # Invoke the app.
            self.subprocess.run(
                [sys.executable, "-m", app.name],
                env=env,
                check=True,
            )
        except subprocess.CalledProcessError:
            print()
            raise BriefcaseCommandError(
                "Unable to start application '{app.name}'".format(
                    app=app
                ))

    def __call__(
        self,
        appname: Optional[str] = None,
        update_dependencies: Optional[bool] = False,
        **kwargs
    ):
        # Which app should we run? If there's only one defined
        # in pyproject.toml, then we can use it as a default;
        # otherwise look for a -a/--app option.
        if len(self.apps) == 1:
            app = list(self.apps.values())[0]
        elif appname:
            try:
                app = self.apps[appname]
            except KeyError:
                raise BriefcaseCommandError(
                    "Project doesn't define an application named '{appname}'".format(
                        appname=appname
                    ))
        else:
            raise BriefcaseCommandError(
                "Project specifies more than one application; "
                "use --app to specify which one to start."
            )

        # Look for the existence of a dist-info file.
        # If one exists, assume that the dependencies have already been
        # installed. If a dependency update has been manually requested,
        # do it regardless.
        dist_info_path = self.app_module_path(app).parent / '{app.module_name}.dist-info'.format(app=app)
        if update_dependencies or not dist_info_path.exists():
            self.install_local_dependencies(app, **kwargs)
            write_dist_info(app, dist_info_path)

        state = self.run_local_app(app, **kwargs)
        return state
