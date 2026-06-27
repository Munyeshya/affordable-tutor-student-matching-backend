from tutors.models import TutorVerification


def get_marketplace_ready_tutor_ids():
    return [
        verification.tutor_id
        for verification in TutorVerification.objects.select_related("tutor").prefetch_related("documents").filter(status=TutorVerification.Status.APPROVED)
        if verification.is_marketplace_ready()
    ]
