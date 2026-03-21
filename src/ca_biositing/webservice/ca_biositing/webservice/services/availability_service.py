"""Service layer for resource availability data operations.

This module provides business logic for querying resource availability
(from_month, to_month) from the database.
"""

from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ca_biositing.datamodels.models import (
    Resource,
    ResourceAvailability,
)
from ca_biositing.webservice.exceptions import (
    ResourceNotFoundException,
)


class AvailabilityService:
    """Business logic for resource availability data operations."""

    @staticmethod
    def _get_resource_by_name(session: Session, resource_name: str) -> Resource:
        """Get resource by name.

        Args:
            session: Database session
            resource_name: Resource name

        Returns:
            Resource object

        Raises:
            ResourceNotFoundException: If resource not found
        """
        stmt = select(Resource).where(Resource.name == resource_name)
        resource = session.execute(stmt).scalar_one_or_none()

        if not resource:
            raise ResourceNotFoundException(resource_name)

        return resource

    @staticmethod
    def get_by_resource(
        session: Session,
        resource: str,
        geoid: str
    ) -> dict:
        """Get availability data by resource name and geoid.

        Args:
            session: Database session
            resource: Resource name
            geoid: Geographic identifier

        Returns:
            Dictionary with resource, geoid, from_month, to_month

        Raises:
            ResourceNotFoundException: If resource not found or no availability data
        """
        # Validate resource exists
        resource_obj = AvailabilityService._get_resource_by_name(session, resource)

        # Query resource availability
        stmt = (
            select(ResourceAvailability)
            .where(and_(
                ResourceAvailability.resource_id == resource_obj.id,
                ResourceAvailability.geoid == geoid
            ))
        )
        availability = session.execute(stmt).scalar_one_or_none()

        if not availability:
            raise ResourceNotFoundException(
                f"{resource} (no availability data for geoid {geoid})"
            )

        return {
            "resource": resource,
            "geoid": geoid,
            "from_month": availability.from_month,
            "to_month": availability.to_month,
        }

    @staticmethod
    def list_resources(session: Session) -> list[str]:
        """Return distinct resource names that have availability data."""
        stmt = (
            select(Resource.name)
            .join(ResourceAvailability, ResourceAvailability.resource_id == Resource.id)
            .distinct()
            .order_by(Resource.name)
        )
        return [r for (r,) in session.execute(stmt).all()]

    @staticmethod
    def list_geoids(session: Session) -> list[str]:
        """Return distinct geoids that have availability data."""
        stmt = (
            select(ResourceAvailability.geoid)
            .distinct()
            .order_by(ResourceAvailability.geoid)
        )
        return [g for (g,) in session.execute(stmt).all()]
