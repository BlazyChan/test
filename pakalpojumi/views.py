from django.shortcuts import render, redirect
from .forms import PasutijumaVeidlapa
from django.contrib import messages
from .models import PakalpojumaVeids, Pasutijums, BilzuGalerija, Bilde
from django.core.serializers.json import DjangoJSONEncoder
from django.core import serializers
from lietotaji.models import Fotografs
import base64
from django.core.files.base import ContentFile
import io
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys


# Lapas "Pasūtīt" mainīgie:
gala_bildes = None
gala_galerija = None


# Sākumlapa (pirmā lapa, ko redz atverot mājaslapu):
def sakumlapa(request):
    return render(request, 'sakumlapa.html', {})


# Lapa, kur lietotājs var veikt pasūtījumus, jeb pasūtīt pakalpojumus:
def pasutit(request):
    if request.user.is_anonymous is False:
        global gala_bildes
        global gala_galerija

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == "POST":
            gala_bildes = request.POST.getlist('django_bildes[]')
            form = PasutijumaVeidlapa()

        elif request.method == "POST":
            form = PasutijumaVeidlapa(request.POST)
            if form.is_valid():
                instance = form.save(commit=False)
                instance.lietotajs = request.user
                instance.pakalpojuma_veids = PakalpojumaVeids.objects.get(nosaukums=instance.pakalpojuma_veids)
                instance.save()

                # Izveido jaunu bilžu galeriju:
                gala_galerija = BilzuGalerija.objects.create(
                    nosaukums=str(instance.pakalpojuma_veids) + " - " + request.user.vards + " " + request.user.uzvards + " (" + str(instance.pasutijuma_datums) + ")", pasutijums=instance)

                # Veiksmīga pasūtījuma izveidošanas gadījumā - lietotāju aizved uz norādīto lapu un izvada ziņu:
                messages.success(request, "Pasūtījums tika veiksmīgi izveidots!")
                return redirect('/pasutit/')
        else:
            form = PasutijumaVeidlapa()

        vaicajums = PakalpojumaVeids.objects.filter()
        # Pārveido modeli par JSON simbolu virkni:
        vaicajums = serializers.serialize("json", vaicajums, cls=DjangoJSONEncoder)

        # Ja abi mainīgie eksistē, tad izveido bildes objektus:
        if gala_bildes and gala_galerija:
            bilzu_galerija = gala_galerija
            bildes = gala_bildes
            for bilde in bildes:
                base64_fails = bilde.split("base64,")[1]
                satura_veids = bilde.split(";")[0].split("data:")[1].split("+")[0]
                bildes_nosaukums = "bilde" + "." + satura_veids.split("/")[1]

                f = io.BytesIO(base64.b64decode(base64_fails))
                bilde = InMemoryUploadedFile(f, field_name='picture', name=bildes_nosaukums, content_type=satura_veids,
                                             size=sys.getsizeof(f), charset=None)
                # Izveido bildes objektu:
                Bilde.objects.create(
                    atrasanas_vieta=str('lietotajs_{0}/{1}/'.format(str(request.user.epasts.replace("@", "_")),
                                                                    str(bilzu_galerija.id) + "_" + str(
                                                                        bilzu_galerija.nosaukums))),
                    fails=bilde,
                    lietotajs=request.user,
                    bilzu_galerija=bilzu_galerija
                )
            gala_galerija = None
            gala_bildes = None
        return render(request, 'pasutit.html', {"form": form, "pakalpojumu_apraksti": vaicajums})
    else:
        return redirect("/")


# Lapa, kurā parasts lietotājs var apskatīt savus vai fotogrāfs var apskatīt visus pasūtījumus:
def pasutijumi(request):
    if request.user.is_anonymous is False:
        # Ja lietotājs ir fotogrāfs, tad izvada visus pasūtījumus:
        if Fotografs.objects.filter(lietotajs=request.user.epasts).exists() or request.user.is_superuser:
            virsraksts = "Visi pasūtījumi"
            vaicajums = Pasutijums.objects.all()
        # Ja lietotājs nav fotogrāfs, tad izvada visus šī paša lietotāja pasūtījumus:
        else:
            virsraksts = "Mani pasūtījumi"
            vaicajums = Pasutijums.objects.filter(lietotajs=request.user)
        # Pasūtījumu skaits:
        skaits = vaicajums.count()
        return render(request, 'pasutijumi.html', {"pasutijumi": vaicajums, "virsraksts": virsraksts, "skaits": skaits})
    else:
        return redirect("/")


# Bilžu galerijas lapa (balstoties uz pasūtījumu):
def bilzu_galerijas_saite(request, id):
    pasutijums = Pasutijums.objects.get(id=id)
    if request.user.is_anonymous is False and (request.user == pasutijums.lietotajs or request.user.epasts == pasutijums.fotografs or request.user.is_superuser):
        galerija = BilzuGalerija.objects.get(pasutijums=pasutijums.id)
        bildes = Bilde.objects.filter(bilzu_galerija=galerija.id)
        skaits = bildes.count()
        return render(request, 'galerija.html', {"galerija": galerija, "bildes": bildes, "skaits": skaits})
    else:
        return redirect('/pasutijumi/')
