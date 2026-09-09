from django import forms

from .models import ContactMessage, NewsletterSubscriber, Order, Review

GHANA_REGIONS = [
    ('', 'Select region'),
    ('Greater Accra', 'Greater Accra'),
    ('Ashanti', 'Ashanti'),
    ('Western', 'Western'),
    ('Eastern', 'Eastern'),
    ('Central', 'Central'),
    ('Volta', 'Volta'),
    ('Northern', 'Northern'),
    ('Bono', 'Bono'),
    ('Upper East', 'Upper East'),
    ('Upper West', 'Upper West'),
    ('Ahafo', 'Ahafo'),
    ('Bono East', 'Bono East'),
    ('North East', 'North East'),
    ('Oti', 'Oti'),
    ('Savannah', 'Savannah'),
    ('Western North', 'Western North'),
]


class CheckoutForm(forms.ModelForm):
    region = forms.ChoiceField(choices=GHANA_REGIONS, required=False)

    class Meta:
        model = Order
        fields = [
            'full_name', 'phone_number', 'email', 'delivery_type',
            'address', 'region', 'city', 'landmark',
            'payment_method', 'momo_network', 'notes',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '024 XXX XXXX'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com'}),
            'delivery_type': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'House number, street'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City / Town'}),
            'landmark': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nearest landmark (optional)'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'momo_network': forms.Select(
                choices=[('', 'Select network'), ('MTN', 'MTN Mobile Money'),
                         ('Telecel', 'Telecel Cash'), ('AirtelTigo', 'AirtelTigo Money')],
                attrs={'class': 'form-select'}
            ),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any special requests?'}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('delivery_type') == 'delivery' and not cleaned.get('address'):
            self.add_error('address', 'Please provide a delivery address.')
        if cleaned.get('payment_method') == 'momo' and not cleaned.get('momo_network'):
            self.add_error('momo_network', 'Please select your Mobile Money network.')
        return cleaned


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(
                choices=[(i, f"{i} star{'s' if i != 1 else ''}") for i in range(1, 6)],
                attrs={'class': 'form-select w-auto d-inline-block'}
            ),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Tell us what you thought...'}),
        }


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Your message'}),
        }


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'}),
        }
