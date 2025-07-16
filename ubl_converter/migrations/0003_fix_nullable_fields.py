# ubl_converter/migrations/0003_fix_nullable_fields.py
# Crear este archivo en la carpeta de migraciones

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ubl_converter', '0002_remove_invoice_unique_invoice_per_company_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoiceline',
            name='line_extension_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Valor de Venta'),
        ),
        migrations.AlterField(
            model_name='invoiceline',
            name='igv_amount',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12, null=True, verbose_name='Monto IGV'),
        ),
        migrations.AlterField(
            model_name='invoiceline',
            name='isc_amount',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12, null=True, verbose_name='Monto ISC'),
        ),
        migrations.AlterField(
            model_name='invoiceline',
            name='icbper_amount',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12, null=True, verbose_name='Monto ICBPER'),
        ),
    ]