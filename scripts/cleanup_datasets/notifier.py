#!/usr/bin/env python
"""
notifier.py - Preview pgcleanup actions and notify affected users by email.
"""

import os
import sys

from mako.template import Template

from pgcleanup_lib import (
    Cleanup,
    available_actions,
    build_cleanup_parser,
    parse_cleanup_args,
)

import galaxy.util


DEFAULT_TEMPLATE = "admin_cleanup_warning_template.txt"


def _build_parser():
    parser = build_cleanup_parser(available_actions())
    parser.description = __doc__
    parser.add_argument(
        "--template",
        default=None,
        help="Mako template file to use for email notification. Default: admin_cleanup_warning_template.txt(.sample)",
    )
    parser.add_argument(
        "-i",
        "--info_only",
        action="store_true",
        default=False,
        help="Print notification details, but do not send email",
    )
    parser.add_argument("--no-send", action="store_true", default=False, help="Do not send email")
    parser.add_argument("--smtp", default=None, help="SMTP Server to use to send email")
    parser.add_argument("--fromaddr", default=None, help="From address to use to send email")
    return parser


def _resolve_template_file(template_file):
    if template_file is not None:
        if not os.path.exists(template_file):
            raise FileNotFoundError(f"Specified template file ({template_file}) not found.")
        return template_file
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    default_template = os.path.join(scriptdir, DEFAULT_TEMPLATE)
    if os.path.exists(default_template):
        return default_template
    sample_template_file = f"{default_template}.sample"
    if os.path.exists(sample_template_file):
        return sample_template_file
    raise FileNotFoundError(
        f"Default template ({default_template}) or sample template ({sample_template_file}) not found."
    )


def _resolve_mail_settings(args, config, parser):
    fromaddr = args.fromaddr or config.email_from or ""
    smtp_server = args.smtp or config.smtp_server
    if not (args.no_send or args.info_only) and smtp_server is None:
        parser.error("SMTP Server must be specified as an option (--smtp) or in the config file (smtp_server)")
    if not (args.no_send or args.info_only) and not fromaddr:
        parser.error("From address must be specified as an option (--fromaddr) or in the config file (email_from)")
    return fromaddr, smtp_server


def main(argv=None):
    parser = _build_parser()
    args = parse_cleanup_args(parser, argv=argv)
    try:
        template_file = _resolve_template_file(args.template)
    except FileNotFoundError as exc:
        parser.error(str(exc))
    emailtemplate = Template(filename=template_file)

    with Cleanup(args=args, preview=True) as app:
        fromaddr, smtp_server = _resolve_mail_settings(args, app.config, parser)
        if smtp_server is not None:
            app.config.smtp_server = smtp_server
        notifications = app.preview_notifications()

        if not notifications:
            print("No user notifications to send")
            return 0

        print("##########################################")
        print(f"\n# Previewing cleanup notifications for data older than {args.days} days")
        print(f"# Actions: {', '.join(args.actions)}")
        if args.info_only:
            print("# Displaying info only ( --info_only )\n")
        elif args.no_send:
            print("# Email delivery disabled ( --no-send )\n")

        for email, datasets in sorted(notifications.items()):
            msgtext = emailtemplate.render(email=email, datasets=datasets, cutoff=args.days, actions=args.actions)
            subject = f"Galaxy Server Cleanup - {len(datasets)} datasets pending deletion"
            print()
            print(f"From: {fromaddr}")
            print(f"To: {email}")
            print(f"Subject: {subject}")
            print("----------")
            print(msgtext)
            if not args.no_send and not args.info_only:
                galaxy.util.send_mail(fromaddr, email, subject, msgtext, app.config)

        print("\n##########################################")
    return 0


if __name__ == "__main__":
    sys.exit(main())
