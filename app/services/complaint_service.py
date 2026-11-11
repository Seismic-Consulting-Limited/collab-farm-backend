import uuid
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.complaint_model import (
    Complaint,
    ComplaintAction,
    ComplaintCategory,
    ComplaintMessage,
    ComplaintStatus,
)
from app.models.cooperative_investment_model import Investment
from app.models.package_model import Package
from app.models.user_model import User, UserRole
from app.schemas.complaint_schema import (
    ComplaintPackageOption,
    ComplaintSummaryResponse,
)
from app.utils.cloudinary import upload_kyc_document
from app.services.notification_service import add_notification


MAX_EVIDENCE_SIZE = 5 * 1024 * 1024
ALLOWED_EVIDENCE_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}


class ComplaintService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _package_access_filter(user: User):
        if user.role == UserRole.COOPERATIVE:
            return Package.cooperative_id == user.id
        if user.role == UserRole.INVESTOR:
            return Package.id.in_(
                select(Investment.package_id).where(Investment.investor_id == user.id)
            )
        return None

    @staticmethod
    def _visibility_filter(user: User):
        if user.role == UserRole.ADMIN:
            return None
        if user.role == UserRole.COOPERATIVE:
            return or_(
                Complaint.submitted_by_id == user.id,
                Complaint.package_id.in_(
                    select(Package.id).where(Package.cooperative_id == user.id)
                ),
            )
        return or_(
            Complaint.submitted_by_id == user.id,
            Complaint.package_id.in_(
                select(Investment.package_id).where(Investment.investor_id == user.id)
            ),
        )

    async def get_connected_packages(self, user: User) -> list[ComplaintPackageOption]:
        query = select(Package).order_by(Package.title.asc())
        access_filter = self._package_access_filter(user)
        if access_filter is not None:
            query = query.where(access_filter)
        packages = (await self.session.execute(query)).scalars().all()
        return [ComplaintPackageOption(id=pkg.id, title=pkg.title) for pkg in packages]

    async def _validate_package_access(
        self, user: User, package_id: Optional[uuid.UUID]
    ) -> Optional[Package]:
        if package_id is None:
            return None
        query = select(Package).where(Package.id == package_id)
        access_filter = self._package_access_filter(user)
        if access_filter is not None:
            query = query.where(access_filter)
        package = (await self.session.execute(query)).scalars().first()
        if package is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related package was not found or is not connected to your account.",
            )
        return package

    async def _upload_evidence(self, files: Optional[list[UploadFile]]) -> list[dict]:
        evidence = []
        for file in files or []:
            if file.content_type not in ALLOWED_EVIDENCE_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Evidence must be a PDF, JPEG, PNG, or WebP file.",
                )
            content = await file.read(MAX_EVIDENCE_SIZE + 1)
            if len(content) > MAX_EVIDENCE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Each evidence file must be 5 MB or smaller.",
                )
            await file.seek(0)
            uploaded = await upload_kyc_document(file, "collabfarm/complaint_evidence")
            evidence.append(
                {
                    "file_name": file.filename or "evidence",
                    "content_type": file.content_type,
                    "url": uploaded.get("secure_url"),
                    "public_id": uploaded.get("public_id"),
                }
            )
        return evidence

    @staticmethod
    def _to_read_dict(complaint: Complaint) -> dict:
        return {
            "id": complaint.id,
            "reference": complaint.reference,
            "submitted_by_id": complaint.submitted_by_id,
            "package_id": complaint.package_id,
            "package_title": complaint.package.title if complaint.package else None,
            "subject": complaint.subject,
            "category": complaint.category,
            "description": complaint.description,
            "evidence": complaint.evidence or [],
            "status": complaint.status,
            "acknowledgment_accepted": complaint.acknowledgment_accepted,
            "assigned_reviewer_id": complaint.assigned_reviewer_id,
            "outcome": complaint.outcome,
            "explanation": complaint.explanation,
            "created_at": complaint.created_at,
            "updated_at": complaint.updated_at,
        }

    async def create_complaint(
        self,
        user: User,
        subject: str,
        category: ComplaintCategory,
        description: str,
        package_id: Optional[uuid.UUID],
        acknowledgment_accepted: bool,
        evidence_files: Optional[list[UploadFile]],
    ) -> dict:
        if not acknowledgment_accepted:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must acknowledge the complaint review statement before submitting.",
            )
        package = await self._validate_package_access(user, package_id)
        evidence = await self._upload_evidence(evidence_files)
        complaint = Complaint(
            submitted_by_id=user.id,
            package_id=package.id if package else None,
            subject=subject.strip(),
            category=category,
            description=description.strip(),
            evidence=evidence,
            status=ComplaintStatus.OPEN,
            acknowledgment_accepted=True,
        )
        self.session.add(complaint)
        await self.session.flush()
        self.session.add(
            ComplaintAction(
                complaint_id=complaint.id,
                actor_id=user.id,
                action="COMPLAINT_SUBMITTED",
                description="Complaint submitted",
            )
        )
        admin_ids = (await self.session.execute(
            select(User.id).where(User.role == UserRole.ADMIN)
        )).scalars().all()
        recipients = set(admin_ids)
        if package is not None:
            recipients.add(package.cooperative_id)
        recipients.discard(user.id)
        for recipient_id in recipients:
            add_notification(
                self.session,
                recipient_id,
                "New complaint received",
                f"{user.full_name} submitted a complaint: {subject.strip()}",
                "COMPLAINT_CREATED",
                actor_id=user.id,
                entity_type="complaint",
                entity_id=complaint.id,
                link=f"/complaints/{complaint.id}",
            )
        await self.session.commit()
        await self.session.refresh(complaint)
        complaint.package = package
        return self._to_read_dict(complaint)

    async def get_complaint_summary(
        self,
        user: User,
        search: Optional[str] = None,
        category: Optional[ComplaintCategory] = None,
        status_filter: Optional[ComplaintStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ComplaintSummaryResponse:
        visibility = self._visibility_filter(user)
        base = select(Complaint)
        if visibility is not None:
            base = base.where(visibility)

        counts_query = select(Complaint.status, func.count(Complaint.id))
        if visibility is not None:
            counts_query = counts_query.where(visibility)
        grouped_counts = (await self.session.execute(
            counts_query.group_by(Complaint.status)
        )).all()
        counts = {complaint_status: count for complaint_status, count in grouped_counts}

        query = (
            base.join(User, User.id == Complaint.submitted_by_id)
            .outerjoin(Package, Package.id == Complaint.package_id)
            .options(
                selectinload(Complaint.package),
                selectinload(Complaint.submitted_by),
            )
        )
        if category is not None:
            query = query.where(Complaint.category == category)
        if status_filter is not None:
            query = query.where(Complaint.status == status_filter)
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Complaint.reference.ilike(term),
                    Complaint.subject.ilike(term),
                    User.first_name.ilike(term),
                    User.last_name.ilike(term),
                    User.email.ilike(term),
                    Package.title.ilike(term),
                )
            )

        total = await self.session.scalar(
            select(func.count()).select_from(query.order_by(None).subquery())
        )
        query = query.order_by(Complaint.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        complaints = (await self.session.execute(query)).unique().scalars().all()
        items = []
        for complaint in complaints:
            submitter = complaint.submitted_by
            items.append(
                {
                    "id": complaint.id,
                    "reference": complaint.reference,
                    "subject": complaint.subject,
                    "category": complaint.category,
                    "package_id": complaint.package_id,
                    "package_title": complaint.package.title if complaint.package else None,
                    "raised_by_id": complaint.submitted_by_id,
                    "raised_by_name": submitter.full_name,
                    "raised_by_role": str(getattr(submitter.role, "value", submitter.role)),
                    "status": complaint.status,
                    "created_at": complaint.created_at,
                }
            )

        return ComplaintSummaryResponse(
            total=int(total or 0),
            page=page,
            page_size=page_size,
            open_count=counts.get(ComplaintStatus.OPEN, 0),
            under_review_count=counts.get(ComplaintStatus.UNDER_REVIEW, 0),
            awaiting_response_count=counts.get(ComplaintStatus.AWAITING_RESPONSE, 0),
            resolved_count=counts.get(ComplaintStatus.RESOLVED, 0),
            escalated_count=counts.get(ComplaintStatus.ESCALATED, 0),
            items=items,
        )

    async def _get_authorized_complaint(
        self, user: User, complaint_id: uuid.UUID
    ) -> Complaint:
        query = (
            select(Complaint)
            .options(
                selectinload(Complaint.package)
                .selectinload(Package.cooperative)
                .selectinload(User.cooperative_profile),
                selectinload(Complaint.submitted_by),
                selectinload(Complaint.assigned_reviewer),
                selectinload(Complaint.messages).selectinload(ComplaintMessage.author),
                selectinload(Complaint.actions).selectinload(ComplaintAction.actor),
            )
            .where(Complaint.id == complaint_id)
        )
        visibility = self._visibility_filter(user)
        if visibility is not None:
            query = query.where(visibility)
        complaint = (await self.session.execute(query)).scalars().first()
        if complaint is None:
            raise HTTPException(status_code=404, detail="Complaint not found.")

        return complaint

    async def get_complaint_detail(self, user: User, complaint_id: uuid.UUID) -> dict:
        complaint = await self._get_authorized_complaint(user, complaint_id)
        cooperative = complaint.package.cooperative if complaint.package else None
        cooperative_profile = (
            cooperative.cooperative_profile
            if cooperative and cooperative.cooperative_profile
            else None
        )
        return {
            **self._to_read_dict(complaint),
            "raised_by_name": complaint.submitted_by.full_name,
            "raised_by_role": str(
                getattr(complaint.submitted_by.role, "value", complaint.submitted_by.role)
            ),
            "cooperative_id": cooperative.id if cooperative else None,
            "cooperative_name": (
                cooperative_profile.cooperative_name if cooperative_profile else None
            ),
            "reviewer_name": (
                complaint.assigned_reviewer.full_name
                if complaint.assigned_reviewer
                else None
            ),
            "messages": [
                {
                    "id": message.id,
                    "author_id": message.author_id,
                    "author_name": message.author.full_name,
                    "author_role": str(
                        getattr(message.author.role, "value", message.author.role)
                    ),
                    "message": message.message,
                    "evidence": message.evidence or [],
                    "created_at": message.created_at,
                }
                for message in sorted(complaint.messages, key=lambda item: item.created_at)
            ],
            "actions": [
                {
                    "id": action.id,
                    "action": action.action,
                    "description": action.description,
                    "actor_id": action.actor_id,
                    "actor_name": action.actor.full_name if action.actor else "System",
                    "created_at": action.created_at,
                }
                for action in sorted(complaint.actions, key=lambda item: item.created_at)
            ],
        }

    async def post_message(
        self,
        user: User,
        complaint_id: uuid.UUID,
        message: str,
        evidence_files: Optional[list[UploadFile]],
    ) -> dict:
        complaint = await self._get_authorized_complaint(user, complaint_id)
        evidence = await self._upload_evidence(evidence_files)
        new_message = ComplaintMessage(
            complaint_id=complaint.id,
            author_id=user.id,
            message=message.strip(),
            evidence=evidence,
        )
        self.session.add(new_message)
        self.session.add(
            ComplaintAction(
                complaint_id=complaint.id,
                actor_id=user.id,
                action="MESSAGE_POSTED",
                description="A message was added to the complaint",
            )
        )
        recipients = {
            complaint.submitted_by_id,
            complaint.assigned_reviewer_id,
        }
        if complaint.package:
            recipients.add(complaint.package.cooperative_id)
        recipients.discard(None)
        recipients.discard(user.id)
        for recipient_id in recipients:
            add_notification(
                self.session,
                recipient_id,
                "New complaint message",
                f"{user.full_name} added a message to complaint {complaint.reference}.",
                "COMPLAINT_MESSAGE",
                actor_id=user.id,
                entity_type="complaint",
                entity_id=complaint.id,
                link=f"/complaints/{complaint.id}",
            )
        if complaint.status == ComplaintStatus.AWAITING_RESPONSE:
            complaint.status = ComplaintStatus.UNDER_REVIEW
        await self.session.commit()
        await self.session.refresh(new_message)
        return {
            "id": new_message.id,
            "author_id": user.id,
            "author_name": user.full_name,
            "author_role": str(getattr(user.role, "value", user.role)),
            "message": new_message.message,
            "evidence": new_message.evidence or [],
            "created_at": new_message.created_at,
        }

    async def assign_reviewer(
        self, actor: User, complaint_id: uuid.UUID, reviewer_id: uuid.UUID
    ) -> dict:
        if actor.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only reviewers can assign a reviewer.")
        complaint = await self._get_authorized_complaint(actor, complaint_id)
        reviewer = (await self.session.execute(
            select(User).where(User.id == reviewer_id, User.role == UserRole.ADMIN)
        )).scalars().first()
        if reviewer is None:
            raise HTTPException(status_code=404, detail="Reviewer not found.")
        complaint.assigned_reviewer_id = reviewer.id
        if complaint.status == ComplaintStatus.OPEN:
            complaint.status = ComplaintStatus.UNDER_REVIEW
        self.session.add(
            ComplaintAction(
                complaint_id=complaint.id,
                actor_id=actor.id,
                action="REVIEWER_ASSIGNED",
                description=f"Reviewer assigned: {reviewer.full_name}",
            )
        )
        add_notification(
            self.session,
            complaint.submitted_by_id,
            "Reviewer assigned",
            f"A reviewer has been assigned to complaint {complaint.reference}.",
            "COMPLAINT_REVIEWER_ASSIGNED",
            actor_id=actor.id,
            entity_type="complaint",
            entity_id=complaint.id,
            link=f"/complaints/{complaint.id}",
        )
        await self.session.commit()
        return {"assigned_reviewer_id": reviewer.id, "reviewer_name": reviewer.full_name}

    async def update_status(
        self,
        actor: User,
        complaint_id: uuid.UUID,
        new_status: ComplaintStatus,
        outcome: Optional[str] = None,
        explanation: Optional[str] = None,
    ) -> dict:
        if actor.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only reviewers can update complaint status.")
        complaint = await self._get_authorized_complaint(actor, complaint_id)
        if new_status == ComplaintStatus.RESOLVED and not explanation:
            raise HTTPException(
                status_code=422,
                detail="An explanation is required when resolving a complaint.",
            )
        old_status = complaint.status
        complaint.status = new_status
        if new_status == ComplaintStatus.RESOLVED:
            complaint.outcome = outcome or "REVIEW_COMPLETED"
            complaint.explanation = explanation
        self.session.add(
            ComplaintAction(
                complaint_id=complaint.id,
                actor_id=actor.id,
                action="STATUS_CHANGED",
                description=(
                    f"Status changed from {old_status.value} to {new_status.value}"
                    + (f". {explanation}" if explanation else "")
                ),
            )
        )
        add_notification(
            self.session,
            complaint.submitted_by_id,
            "Complaint status updated",
            f"Complaint {complaint.reference} is now {new_status.value.replace('_', ' ').title()}.",
            "COMPLAINT_STATUS",
            actor_id=actor.id,
            entity_type="complaint",
            entity_id=complaint.id,
            link=f"/complaints/{complaint.id}",
        )
        await self.session.commit()
        return {"status": complaint.status, "outcome": complaint.outcome}

    async def appeal(self, user: User, complaint_id: uuid.UUID, reason: str) -> dict:
        complaint = await self._get_authorized_complaint(user, complaint_id)
        if complaint.submitted_by_id != user.id:
            raise HTTPException(
                status_code=403, detail="Only the person who raised the complaint may appeal."
            )
        if complaint.status != ComplaintStatus.RESOLVED:
            raise HTTPException(
                status_code=409, detail="A complaint can be appealed after it is resolved."
            )
        complaint.status = ComplaintStatus.ESCALATED
        self.session.add(
            ComplaintAction(
                complaint_id=complaint.id,
                actor_id=user.id,
                action="APPEALED",
                description=f"Complaint appealed: {reason.strip()}",
            )
        )
        admin_ids = (await self.session.execute(
            select(User.id).where(User.role == UserRole.ADMIN)
        )).scalars().all()
        for recipient_id in set(admin_ids) - {user.id}:
            add_notification(
                self.session,
                recipient_id,
                "Complaint appealed",
                f"Complaint {complaint.reference} was appealed.",
                "COMPLAINT_APPEALED",
                actor_id=user.id,
                entity_type="complaint",
                entity_id=complaint.id,
                link=f"/complaints/{complaint.id}",
            )
        await self.session.commit()
        return {"status": complaint.status}
