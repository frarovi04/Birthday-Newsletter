from django.db import migrations


def create_default_emailconfigs(apps, schema_editor):
    EmailConfig = apps.get_model("api", "EmailConfig")

    # Config 1: template per chi NON festeggia
    EmailConfig.objects.update_or_create(
        pk=1,
        defaults={
            "subject_template": "Compleanni del team {team} di {location} - {date}",
            "body_template": (
                "Buongiorno team {team} di {location},\n\n"
                "Ecco chi compie gli anni oggi:\n"
                "{employees}\n\n"
                "Fai loro gli auguri!"
            ),
            "sender_email": "no-reply@birthdaynewsletter.com",
        },
    )

    # Config 2: template per chi festeggia
    EmailConfig.objects.update_or_create(
        pk=2,
        defaults={
            "subject_template": "Buon compleanno {first_name}!",
            "body_template": (
                "Ciao {first_name},\n\n"
                "tanti auguri di buon compleanno!\n\n"
                "Nel team {team} di {location} festeggiano anche:\n"
                "{employees}\n\n"
                "Goditi la giornata!"
            ),
            "sender_email": "no-reply@birthdaynewsletter.com",
        },
    )


def delete_default_emailconfigs(apps, schema_editor):
    EmailConfig = apps.get_model("api", "EmailConfig")
    EmailConfig.objects.filter(pk__in=[1, 2]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0002_emailconfig"),
    ]

    operations = [
        migrations.RunPython(create_default_emailconfigs, delete_default_emailconfigs),
    ]

