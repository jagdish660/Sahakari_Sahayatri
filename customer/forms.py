from customer.models import Member
from django import forms

class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['member_id', 'first_name', 'middle_name', 'last_name', 'email', 'phone_number', 'address', 'date_of_birth', 'citizenship_number', 'occupation']
        widgets = {
            'member_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'citizenship_number': forms.TextInput(attrs={'class': 'form-control'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control'}),
        }

class UpdateMemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['first_name', 'middle_name', 'last_name', 'email', 'phone_number', 'address', 'date_of_birth', 'occupation']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control'}),
        }

class UserUpdateMemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['email', 'phone_number', 'address', 'occupation']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'occupation': forms.TextInput(attrs={'class': 'form-control'}),
        }
