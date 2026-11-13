from django import forms
from django.core.validators import MinValueValidator

from .models import Order, Product, ProductSKU


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'subcategory', 'price', 'original_price', 'stock',
                  'description', 'is_active', 'is_featured']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select', 'id': 'categorySelect'}),
            'subcategory': forms.Select(attrs={'class': 'form-select', 'id': 'subcategorySelect'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'original_price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('price', 'original_price'):
            self.fields[name].validators.append(MinValueValidator(0))
        self.fields['category'].empty_label = '请选择一级类目'
        self.fields['subcategory'].empty_label = '请选择二级类目'
        if self.instance.pk:
            self.fields['category'].disabled = True
            self.fields['subcategory'].disabled = True
        try:
            category_id = self.fields['category'].to_python(self['category'].value())
        except forms.ValidationError:
            category_id = None
        self.fields['subcategory'].queryset = self.fields['subcategory'].queryset.filter(category=category_id)

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get('category')
        subcategory = cleaned.get('subcategory')
        if category and subcategory and subcategory.category_id != category.pk:
            self.add_error('subcategory', '请选择所属一级类目下的二级类目')
        return cleaned


class SKUValuesForm(forms.ModelForm):
    class Meta:
        model = ProductSKU
        fields = ['price', 'stock']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['price'].validators.append(MinValueValidator(0))


class OrderForm(forms.ModelForm):
    quantity = forms.IntegerField(label='购买数量', min_value=1, max_value=2147483647, widget=forms.NumberInput(
        attrs={'class': 'form-control', 'style': 'width: 120px;'}
    ))

    class Meta:
        model = Order
        fields = ['contact_name', 'contact_phone', 'address', 'quantity', 'note']
        widgets = {
            'contact_name': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'name'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'type': 'tel', 'autocomplete': 'tel'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'autocomplete': 'street-address'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
