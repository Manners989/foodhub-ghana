# Generated for the Paystack payment integration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='is_paid',
            field=models.BooleanField(
                default=False,
                help_text="True once Paystack confirms a successful charge. Always False for cash on delivery until the order is fulfilled.",
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_reference',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Paystack transaction reference used to verify this order's payment.",
                max_length=100,
            ),
        ),
    ]
