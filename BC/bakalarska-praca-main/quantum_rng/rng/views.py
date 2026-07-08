import traceback

from django.db.models import Sum
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.contrib import messages

from .models import QuantumShotResult
from .utils.utils import load_local_results, get_distributions, analyze_bitstream, analyze_bitstream_nist, \
    dieharder_tests_chart, next_bit_test_crossval, analyze_bitstream_extracted
from .utils.QuantumDBStream import QuantumDBStream, reset_quantum_database  # your QuantumDBStream class
import io, base64
import matplotlib.pyplot as plt
from django.shortcuts import render
import matplotlib
from accounts.models import RNGHistory
from accounts.models import Profile

matplotlib.use('Agg')        # must be called before pyplot import


def main_page(request):
    return render(request, "main.html")

def dice_page(request):
    if request.method == "POST":
        try:
            dice_type = request.POST.get("dice_type")
            count = int(request.POST.get("count", 1))

            # Validate
            if dice_type not in ["14", "16", "18", "110" , "112" , "120" , "150" , "1100"]:
                messages.error(request, "Invalid dice type.")
                return redirect("dice_page")

            if count < 1:
                messages.error(request, "You must roll at least one dice.")
                return redirect("dice_page")

            if count > 6:
                messages.warning(request, "Maximum is 6 dice at once. Showing 6 rolls.")
                count = 6

            # Dice bounds
            dice_map = {
                "14": (1, 4),
                "16": (1, 6),
                "18": (1, 8),
                "110": (1, 10),
                "112": (1, 12),
                "120": (1, 20),
                "150": (1, 50),
                "1100": (1, 100),
            }

            low, high = dice_map[dice_type]

            stream = QuantumDBStream()
            results = [stream.get_random(low, high) for _ in range(count)]

            if request.user.is_authenticated:
                RNGHistory.objects.create(
                    user=request.user,
                    generator_type="dice",
                    params={"dice_type": dice_type, "count": count},
                    result=results,
                )

            return render(
                request,
                "generators/dice.html",
                {
                    "results": results,
                    "dice_type": dice_type,
                    "count": count,
                }
            )

        except ValueError:
            messages.error(request, "Invalid number input.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    return render(request, "generators/dice.html")


def coin_page(request):
    if request.method == "POST":
        try:
            coins = int(request.POST.get("coin", 1))

            # ---- Validate ----
            if coins < 1:
                messages.error(request, "You must flip at least one coin.")
                return redirect("coin_page")

            if coins > 6:
                messages.warning(request, "Maximum allowed is 6 flips at once.")
                coins = 6

            # ---- Generate Results ----
            stream = QuantumDBStream()
            results = [stream.get_random(1, 2) for _ in range(coins)]
            if request.user.is_authenticated:
                RNGHistory.objects.create(
                    user=request.user,
                    generator_type="coin",
                    params={"count": coins},
                    result=results,
                )
            return render(
                request,
                "generators/coin.html",
                {
                    "random_results": results,
                    "coin": coins,
                }
            )
        except ValueError:
            messages.error(request, "Invalid input. Enter a number.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    return render(request, "generators/coin.html")


def generator_page(request):
    context = {}

    if request.method == "POST":
        try:
            from_val = int(request.POST.get("from_val"))
            to_val = int(request.POST.get("to_val"))

            stream = QuantumDBStream()
            result = stream.get_random(from_val, to_val)
            context["random_result"] = result
            context["from_val"] = from_val
            context["to_val"] = to_val

            if request.user.is_authenticated:
                RNGHistory.objects.create(
                    user=request.user,
                    generator_type="generator",
                    params={"from_val": from_val , "to_val" : to_val},
                    result=result,
                )
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    return render(request,"generators/generator.html" ,context)

def about_page(request):
    return render(request, "about.html")

def api_page(request):
    return render(request, "api.html")

def charts_page(request):
    try:
        # --- get distributions (may be the expensive part) ---
        dist_d6, dist_d16, total_d6, total_d16 = get_distributions()

        # Helper to render a bar chart to base64 PNG
        def render_bar_chart(values, counts, title, xlabel="Value", ylabel="Count", color="#00bfff"):
            # create figure with controlled size/dpi, tight layout
            fig, ax = plt.subplots(figsize=(8, 4), dpi=90)
            ax.bar(values, counts, color=color, edgecolor="black", linewidth=0.5)
            ax.set_title(title, fontsize=12)
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.grid(axis='y', linestyle='--', alpha=0.25)
            plt.tight_layout()

            buf = io.BytesIO()
            try:
                fig.savefig(buf, format="png", bbox_inches='tight')
                buf.seek(0)
                encoded = base64.b64encode(buf.read()).decode("ascii")
                return encoded
            finally:
                buf.close()
                plt.close(fig)

        # Chart 1: Dice (1..6)
        values1 = list(range(1, 7))
        counts1 = [int(dist_d6.get(v, 0)) for v in values1]
        chart1 = render_bar_chart(
            values1,
            counts1,
            title=f"Distribution of Dice Rolls (1–6) — Total: {total_d6}",
            color="#00bfff"
        )

        # Chart 2: 4-bit numbers (0..15)
        values2 = list(range(0, 16))
        counts2 = [int(dist_d16.get(v, 0)) for v in values2]
        chart2 = render_bar_chart(
            values2,
            counts2,
            title=f"Distribution of 4-bit Numbers (0–15) — Total: {total_d16}",
            color="#ffa500"
        )

        # bias  = get_bias()
        # print(bias)

        analysisBias = analyze_bitstream( n_splits=10)
        analysisBiasExtracted = analyze_bitstream_extracted( n_splits=10)
        nistAnalyze = analyze_bitstream_nist()
        dieharderAnalyze = dieharder_tests_chart()
        nextBitTestAnalyze = next_bit_test_crossval(window_size=8, n_splits=10)

        context = {
            "chart1": chart1,
            "chart2": chart2,
            "total_d6": total_d6,
            "total_d16": total_d16,
            "analysis" : analysisBias,
            "analysisExtracted" : analysisBiasExtracted,
            # "bias" : bias,

            "nistAnalyzeChart": nistAnalyze['chart'],
            "nistAnalyze":nistAnalyze['results'],

            "dieharderAnalyze" : dieharderAnalyze['results'],
            "dieharderAnalyzeChart" : dieharderAnalyze['chart'],

            "nextBitTestAnalyze" : nextBitTestAnalyze['results'],
            "nextBitTestAnalyzeChart" : nextBitTestAnalyze['chart'],
        }
        return render(request, "charts.html", context)

    except Exception as e:
        # log full traceback to console / logs for debugging
        print("Error generating charts:", e)
        traceback.print_exc()

        # Fail gracefully: render a template with the error message
        return render(request, "charts.html", {
            "chart1": None,
            "chart2": None,
            "error": "Unable to generate charts right now. See server logs for details.",
        })


def administration_page(request):
    if request.user.profile.user_type != "admin":
        return HttpResponseForbidden("You are not allowed to access this page.")

    # ---- NEW STATISTICS ----
    # 1. Count total users
    user_count = Profile.objects.count()

    # 2. Get QRNG statistics
    qrng_entries = QuantumShotResult.objects.all()
    entry_count = qrng_entries.count()

    total_used_bits = QuantumShotResult.objects.aggregate(total=Sum("used_bits"))["total"]

    # each entry has 25 bits
    total_bits = entry_count * 25
    if total_used_bits :
        bits_left = total_bits - total_used_bits
    else:
        bits_left = 0

    # ---- Handle buttons ----
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "load":
            count = load_local_results("results1000shot.json")
            messages.success(request, f"Correctly added {count} results from local JSON.")
            return redirect("administration_page")

        if action == "users":
            return redirect("users_page")

        if action == "reset":
            reset_quantum_database()
            messages.success(request, f"The database was reset")
            return redirect("main_page")

    # ---- Render template with new data ----
    context = {
        "user_count": user_count,
        "total_used_bits": total_used_bits,
        "bits_left": bits_left,
        "total_bits": entry_count*25,
    }

    return render(request, "administration.html", context)


