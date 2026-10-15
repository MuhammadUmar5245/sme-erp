"""Help & support page and user evaluation of the ERP (report 5.1.4 User Evaluation, 5.2.1 Technical Support)."""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import BootstrapModelForm
from .models import SystemFeedback

SUPPORT = {
    "help_desk_email": "erp-support@alwadi.om",
    "help_desk_phone": "+968 2448 1299 (Sun–Thu 08:00–17:00)",
    "whatsapp": "+968 9100 1299",
    "response_targets": [("Critical (system down, cannot invoice)", "1 hour"), ("High (one module unusable)", "4 hours"),
                         ("Normal (question, minor issue)", "1 working day")],
}


class SystemFeedbackForm(BootstrapModelForm):
    rating = forms.TypedChoiceField(choices=[("", "-")] + [(i, f"{i} - {label}") for i, label in
                                                            [(5, "Excellent"), (4, "Good"), (3, "Average"), (2, "Poor"),
                                                             (1, "Very poor")]],
                                    coerce=int, empty_value=None, required=False)

    class Meta:
        model = SystemFeedback
        fields = ["kind", "area", "rating", "comment"]
        labels = {"kind": "Type", "area": "Which part of the system?"}

    def clean(self):
        data = super().clean()
        if data.get("kind") == SystemFeedback.Kind.RATING and not data.get("rating"):
            self.add_error("rating", "Choose a rating.")
        if data.get("kind") in (SystemFeedback.Kind.PROBLEM, SystemFeedback.Kind.SUGGESTION) and not data.get("comment"):
            self.add_error("comment", "Please describe the problem or suggestion.")
        return data


@login_required
def support(request):
    form = SystemFeedbackForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        feedback = form.save(commit=False)
        feedback.user = request.user
        feedback.save()
        messages.success(request, "Thank you - your feedback was sent to the ERP team.")
        return redirect("core:support")
    return render(request, "core/support.html", {"title": "Help & support", "form": form, "support": SUPPORT,
                                                 "mine": SystemFeedback.objects.filter(user=request.user)[:5]})


def evaluation_summary():
    by_area = (SystemFeedback.objects.values("area")
               .annotate(avg=Avg("rating"), ratings=Count("rating"),
                         problems=Count("id", filter=Q(kind=SystemFeedback.Kind.PROBLEM)),
                         open=Count("id", filter=Q(status=SystemFeedback.Status.OPEN, kind=SystemFeedback.Kind.PROBLEM)))
               .order_by("area"))
    labels = dict(SystemFeedback.Area.choices)
    rows = [{**row, "label": labels.get(row["area"], row["area"])} for row in by_area]
    overall = SystemFeedback.objects.aggregate(avg=Avg("rating"), count=Count("rating"))
    return {"rows": rows, "overall": overall}


@login_required
@permission_required("core.view_systemfeedback", raise_exception=True)
def feedback_overview(request):
    return render(request, "core/feedback_overview.html", {
        "title": "User evaluation", "summary": evaluation_summary(),
        "items": SystemFeedback.objects.select_related("user")[:100]})


@login_required
@permission_required("core.change_systemfeedback", raise_exception=True)
@require_POST
def feedback_resolve(request, pk):
    item = get_object_or_404(SystemFeedback, pk=pk)
    item.status = SystemFeedback.Status.RESOLVED
    item.save(update_fields=["status"])
    return redirect("core:feedback_overview")
