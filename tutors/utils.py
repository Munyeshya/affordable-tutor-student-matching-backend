from catalog.models import TutorSubject
from tutors.models import TutorAgreement, TutorProfile, TutorVerification


def build_tutor_setup_status(user):
    profile = TutorProfile.objects.filter(user=user).first()
    verification = TutorVerification.objects.filter(tutor=user).first()
    agreement = TutorAgreement.objects.filter(tutor=user).first()
    subject_count = TutorSubject.objects.filter(tutor=user).count()
    documents_count = verification.documents.count() if verification else 0

    steps = [
        {
            "key": "profile",
            "label": "Create tutor profile",
            "completed": bool(profile and profile.full_name),
        },
        {
            "key": "subjects",
            "label": "Add subjects and levels",
            "completed": subject_count > 0,
        },
        {
            "key": "documents",
            "label": "Upload ID and certificate",
            "completed": bool(verification and verification.has_required_documents()),
        },
        {
            "key": "agreement",
            "label": "Sign agreement",
            "completed": bool(agreement and agreement.status == TutorAgreement.Status.SIGNED and agreement.agreed_to_terms and agreement.signed_file),
        },
        {
            "key": "approval",
            "label": "Admin approval",
            "completed": bool(verification and verification.status == TutorVerification.Status.APPROVED),
        },
    ]

    missing_steps = [step["key"] for step in steps if not step["completed"]]
    completed_steps = len(steps) - len(missing_steps)
    completion_percentage = round((completed_steps / len(steps)) * 100) if steps else 0

    return {
        "profile": profile,
        "verification": verification,
        "agreement": agreement,
        "subject_count": subject_count,
        "documents_count": documents_count,
        "steps": steps,
        "missing_steps": missing_steps,
        "completion_percentage": completion_percentage,
    }


def get_marketplace_ready_tutor_ids():
    return [
        verification.tutor_id
        for verification in TutorVerification.objects.select_related("tutor").prefetch_related("documents").filter(status=TutorVerification.Status.APPROVED)
        if verification.is_marketplace_ready()
    ]
