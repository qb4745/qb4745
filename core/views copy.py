import random
import string

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.generic import ListView, DetailView, View, TemplateView

from .forms import CheckoutForm, CouponForm, RefundForm, PaymentForm
from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund, UserProfile

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

def products(request):
    context = {
        'items': Item.objects.all().order_by('name')
    }
    return render(request, "core/products.html", context)

def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid

class HomeView(TemplateView):
    template_name = "core/home.html"



class CategoryItemListView(ListView):
    model = Item
    template_name = 'core/products_category.html'
    context_object_name = 'items'
    paginate_by = 10

    def get_queryset(self):
        category_filter = self.request.GET.get('category')
        if category_filter:
            return Item.objects.filter(category=category_filter).order_by('title')
        else:
            return Item.objects.all().order_by('title')



class Nosotrosview(TemplateView):
    template_name = "core/nosotros.html"


class ItemListView(ListView):
    model = Item
    template_name = 'core/item_category.html'
    context_object_name = 'items'

    def get_queryset(self):
        queryset = super().get_queryset()
        category_filter = self.request.GET.get('category')

        if category_filter:
            queryset = queryset.filter(category=category_filter)

        return queryset

class CheckoutView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            context = {
                'form': form,
                'order': order
            }
            return render(self.request, 'core/checkout.html', context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "No tienes un pedido activo")
            return redirect("core:core-order-summary")

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                use_default_shipping = form.cleaned_data.get('use_default_shipping')
                if use_default_shipping:
                    shipping_address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='S',
                        default=True
                    )
                    if shipping_address_qs.exists():
                        shipping_address = shipping_address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No hay una dirección de envío por defecto disponible")
                        return redirect('core:core-checkout')
                else:
                    print("El usuario está ingresando una nueva dirección de envío")
                    shipping_address1 = form.cleaned_data.get('shipping_address')
                    shipping_address2 = form.cleaned_data.get('shipping_address2')
                    shipping_country = form.cleaned_data.get('shipping_country')
                    shipping_zip = form.cleaned_data.get('shipping_zip')

                    if is_valid_form([shipping_address1, shipping_country, shipping_zip]):
                        shipping_address = Address(
                            user=self.request.user,
                            street_address=shipping_address1,
                            apartment_address=shipping_address2,
                            country=shipping_country,
                            zip=shipping_zip,
                            address_type='S'
                        )
                        shipping_address.save()

                        order.shipping_address = shipping_address
                        order.save()

                        set_default_shipping = form.cleaned_data.get('set_default_shipping')
                        if set_default_shipping:
                            shipping_address.default = True
                            shipping_address.save()
                    else:
                        messages.info(
                            self.request, "Por favor, completa los campos requeridos de la dirección de envío")

                use_default_billing = form.cleaned_data.get('use_default_billing')
                same_billing_address = form.cleaned_data.get('same_billing_address')

                if same_billing_address:
                    billing_address = shipping_address
                    billing_address.pk = None
                    billing_address.save()
                    billing_address.address_type = 'B'
                    billing_address.save()
                    order.billing_address = billing_address
                    order.save()
                elif use_default_billing:
                    print("Utilizando la dirección de facturación por defecto")
                    billing_address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='B',
                        default=True
                    )
                    if billing_address_qs.exists():
                        billing_address = billing_address_qs[0]
                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No hay una dirección de facturación por defecto disponible")
                        return redirect('core:core-checkout')
                else:
                    print("El usuario está ingresando una nueva dirección de facturación")
                    billing_address1 = form.cleaned_data.get('billing_address')
                    billing_address2 = form.cleaned_data.get('billing_address2')
                    billing_country = form.cleaned_data.get('billing_country')
                    billing_zip = form.cleaned_data.get('billing_zip')

                    if is_valid_form([billing_address1, billing_country, billing_zip]):
                        billing_address = Address(
                            user=self.request.user,
                            street_address=billing_address1,
                            apartment_address=billing_address2,
                            country=billing_country,
                            zip=billing_zip,
                            address_type='B'
                        )
                        billing_address.save()

                        order.billing_address = billing_address
                        order.save()

                        set_default_billing = form.cleaned_data.get('set_default_billing')
                        if set_default_billing:
                            billing_address.default = True
                            billing_address.save()
                    else:
                        messages.info(
                            self.request, "Por favor, completa los campos requeridos de la dirección de facturación")

                payment_option = form.cleaned_data.get('payment_option')

                if payment_option == 'S':
                    return redirect('core:core-payment', payment_option='stripe')
                elif payment_option == 'P':
                    return redirect('core:core-payment', payment_option='paypal')
                else:
                    messages.warning(
                        self.request, "Opción de pago inválida seleccionada")
                    return redirect('core:core-checkout')
        except ObjectDoesNotExist:
            messages.warning(self.request, "No tienes un pedido activo")
            return redirect("core:core-order-summary")


class ProductListView(ListView):
    model = Item
    paginate_by = 10
    template_name = "core/products.html"


class ItemDetailView(DetailView):
    model = Item
    template_name = 'core/product.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item = self.get_object()  # Obtener el producto actual
        random_products = Item.objects.exclude(slug=item.slug).order_by('?')[:5]
        context['random_products'] = random_products
        return context


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, 'core/order_summary.html', context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "No tienes un pedido activo")
            return redirect("/")


@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # Verificar si el artículo ya está en el pedido
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, f"Se agregó un { order_item.item.__str__() } a su carrito.")
            return redirect("core:core-order-summary")
        else:
            order.items.add(order_item)
            messages.info(request, f"Se ha agregado  { order_item.item.__str__() } a su carrito.")
            return redirect("core:core-order-summary")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, f"Se ha agregado  { order_item.item.__str__() } a su carrito.")
        return redirect("core:core-order-summary")

@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # verificar si el artículo está en el pedido
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            order_item.delete()
            messages.info(request, f"{ order_item.item.__str__() } fue eliminado de su carrito.")
            return redirect("core:core-order-summary")
        else:
            messages.info(request, "Este artículo no estaba en tu carrito")
            return redirect("core:core-product", slug=slug)
    else:
        messages.info(request, "No tienes un pedido activo")
        return redirect("core:core-product", slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # verificar si el artículo está en el pedido
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, f"Se quitó un { order_item.item.__str__() } a su carrito.")
            return redirect("core:core-order-summary")
        else:
            messages.info(request, "Este artículo no estaba en tu carrito")
            return redirect("core:core-product", slug=slug)
    else:
        messages.info(request, "No tienes un pedido activo")
        return redirect("core:core-product", slug=slug)


def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "Este cupón no existe")
        return redirect("core:core-checkout")


class PaymentView(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {
                'order': order,
                'DISPLAY_COUPON_FORM': False,
                'STRIPE_PUBLIC_KEY' : settings.STRIPE_PUBLIC_KEY
            }
            userprofile = self.request.user.userprofile
            if userprofile.one_click_purchasing:
                # obtener la lista de tarjetas del usuario
                cards = stripe.Customer.list_sources(
                    userprofile.stripe_customer_id,
                    limit=3,
                    object='card'
                )
                card_list = cards['data']
                if len(card_list) > 0:
                    # actualizar el contexto con la tarjeta predeterminada
                    context.update({
                        'card': card_list[0]
                    })
            return render(self.request, "core/payment.html", context)
        else:
            messages.warning(
                self.request, "No has agregado una dirección de facturación")
            return redirect("core:core-checkout")

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        form = PaymentForm(self.request.POST)
        userprofile = UserProfile.objects.get(user=self.request.user)
        if form.is_valid():
            token = form.cleaned_data.get('stripeToken')
            save = form.cleaned_data.get('save')
            use_default = form.cleaned_data.get('use_default')

            if save:
                if userprofile.stripe_customer_id != '' and userprofile.stripe_customer_id is not None:
                    customer = stripe.Customer.retrieve(
                        userprofile.stripe_customer_id)
                    customer.sources.create(source=token)

                else:
                    customer = stripe.Customer.create(
                        email=self.request.user.email,
                    )
                    customer.sources.create(source=token)
                    userprofile.stripe_customer_id = customer['id']
                    userprofile.one_click_purchasing = True
                    userprofile.save()

            amount = int(order.get_total() * 100)

            try:

                if use_default or save:
                    # cobrar al cliente porque no se puede cobrar el token más de una vez
                    charge = stripe.Charge.create(
                        amount=amount,  # centavos
                        currency="usd",
                        customer=userprofile.stripe_customer_id
                    )
                else:
                    # cobrar una sola vez en el token
                    charge = stripe.Charge.create(
                        amount=amount,  # centavos
                        currency="usd",
                        source=token
                    )

                # crear el pago
                payment = Payment()
                payment.stripe_charge_id = charge['id']
                payment.user = self.request.user
                payment.amount = order.get_total()
                payment.save()

                # asignar el pago al pedido

                order_items = order.items.all()
                order_items.update(ordered=True)
                for item in order_items:
                    item.save()

                order.ordered = True
                order.payment = payment
                order.ref_code = create_ref_code()
                order.save()

                messages.success(self.request, "¡Tu pedido se realizó con éxito!")
                return redirect("/")

            except stripe.error.CardError as e:
                body = e.json_body
                err = body.get('error', {})
                messages.warning(self.request, f"{err.get('message')}")
                return redirect("/")

            except stripe.error.RateLimitError as e:
                # Demasiadas solicitudes realizadas a la API demasiado rápido
                messages.warning(self.request, "Error de Demasiadas solicitudes realizadas a la API demasiado rápido")
                return redirect("/")

            except stripe.error.InvalidRequestError as e:
                # Se proporcionaron parámetros no válidos a la API de Stripe
                print(e)
                messages.warning(self.request, "Parámetros no válidos")
                return redirect("/")

            except stripe.error.AuthenticationError as e:
                # Falló la autenticación con la API de Stripe
                # (quizás se cambiaron las claves de la API recientemente)
                messages.warning(self.request, "No autenticado")
                return redirect("/")

            except stripe.error.APIConnectionError as e:
                # Falló la comunicación en red con Stripe
                messages.warning(self.request, "Error de red")
                return redirect("/")

            except stripe.error.StripeError as e:
                # Mostrar un error muy genérico al usuario y tal vez enviar
                # un correo electrónico al administrador
                messages.warning(
                    self.request, "Algo salió mal. No se te cobró. Por favor, intenta nuevamente.")
                return redirect("/")

            except Exception as e:
                # enviar un correo electrónico a nosotros mismos
                messages.warning(
                    self.request, "Ocurrió un error grave. Hemos sido notificados.")
                return redirect("/")

        messages.warning(self.request, "Datos no válidos recibidos")
        return redirect("core/payment/stripe/")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(
                    user=self.request.user, ordered=False)
                order.coupon = get_coupon(self.request, code)
                order.save()
                messages.success(self.request, "Cupón agregado exitosamente")
                return redirect("core:core-checkout")
            except ObjectDoesNotExist:
                messages.info(self.request, "No tienes un pedido activo")
                return redirect("core:core-checkout")



class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form
        }
        return render(self.request, "core/request_refund.html", context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            # editar el pedido
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                # almacenar el reembolso
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, "Se recibió tu solicitud.")
                return redirect("core:core-request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "Este pedido no existe.")
                return redirect("core:core-request-refund")

