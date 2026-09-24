#!/usr/bin/env python
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
SQLAlchemy definition of an IVOA Provenance Relational DB
"""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .settings import settings


class ProvDB:

    def __init__(self, db_string=settings.SQLALCHEMY_DB):
        self.engine = create_engine(
            db_string
        )  # , connect_args={'check_same_thread': False})
        self.Base = declarative_base()
        # self.Base = automap_base()
        # dt_format = u'%(year)04d/%(month)02d/%(day)02dT%(hour)02d:%(min)02d:%(second)02d'
        # dt_regexp = u'(\d+)/(\d+)/(\d+)T(\d+):(\d+):(\d+)'
        # myDateTime = DateTime().with_variant(sqlite.DATETIME(storage_format=dt_format, regexp=dt_regexp), 'sqlite')
        # myDateTime = DateTime().with_variant(sqlite.TIMESTAMP(), 'sqlite')
        myDateTime = DateTime().with_variant(String(19), "sqlite")
        Boolean().with_variant(String(5), "sqlite")

        # Description classes

        class ActivityDescription(self.Base):
            __tablename__ = "ActivityDescription"
            id = Column(String(80), primary_key=True)
            name = Column(String(255))

        class EntityDescription(self.Base):
            __tablename__ = "EntityDescription"
            id = Column(String(80), primary_key=True)
            content_type = Column(String(255), nullable=True)
            access_url = Column(String(255), nullable=True)

        class ParameterDescription(self.Base):
            __tablename__ = "ParameterDescription"
            activity_id = Column(
                String(80), ForeignKey("Activity.id"), primary_key=True
            )
            name = Column(String(255), primary_key=True)
            value = Column(String(255), nullable=True)
            entity_ref = Column(String(255), ForeignKey("Entity.id"), nullable=True)

        class GenerationDescription(self.Base):
            __tablename__ = "GenerationDescription"
            id = Column(String(80), primary_key=True)
            role = Column(String(255), primary_key=True)
            activity_id = Column(
                String(80), ForeignKey("Activity.id"), primary_key=True
            )
            entity_id = Column(String(255), ForeignKey("Entity.id"), nullable=True)

        class UsageDescription(self.Base):
            __tablename__ = "UsageDescription"
            id = Column(String(80), primary_key=True)
            role = Column(String(255), nullable=True)
            entity_id = Column(String(80), ForeignKey("Entity.id"))
            activity_id = Column(String(80), ForeignKey("Activity.id"))

        # Core classes

        class Activity(self.Base):
            __tablename__ = "Activity"
            id = Column(String(80), primary_key=True)
            name = Column(String(255))
            start_time = Column(myDateTime, nullable=True)
            end_time = Column(myDateTime, nullable=True)
            # UWS classes
            phase = Column(String(10))
            quote = Column(Integer(), nullable=True)
            execution_duration = Column(Integer(), nullable=True)
            error = Column(Text(), nullable=True)
            creation_time = Column(myDateTime)
            destruction_time = Column(myDateTime, nullable=True)
            owner = Column(String(64), nullable=True)
            owner_token = Column(String(128), nullable=True)
            run_id = Column(String(64), nullable=True)
            process_id = Column(BigInteger(), nullable=True)

        class Entity(self.Base):
            __tablename__ = "Entity"
            id = Column(String(80), primary_key=True)
            value = Column(String(255), nullable=True)
            file_name = Column(String(255), nullable=True)
            file_dir = Column(String(255), nullable=True)
            hash = Column(String(255), nullable=True)
            creation_time = Column(myDateTime)
            content_type = Column(String(255), nullable=True)
            access_url = Column(String(255), nullable=True)
            owner = Column(String(64))
            result_name = Column(String(255), nullable=True)
            result_value = Column(String(255), nullable=True)

        class Parameter(self.Base):
            __tablename__ = "Parameter"
            activity_id = Column(
                String(80), ForeignKey("Activity.id"), primary_key=True
            )
            name = Column(String(255), primary_key=True)
            value = Column(String(255), nullable=True)
            entity_ref = Column(String(255), ForeignKey("Entity.id"), nullable=True)

        class WasGeneratedBy(self.Base):
            __tablename__ = "WasGeneratedBy"
            id = Column(String(80), primary_key=True)
            role = Column(String(255), primary_key=True)
            activity_id = Column(
                String(80), ForeignKey("Activity.id"), primary_key=True
            )
            entity_id = Column(String(255), ForeignKey("Entity.id"), nullable=True)

        class Used(self.Base):
            __tablename__ = "Used"
            id = Column(String(80), primary_key=True)
            role = Column(String(255), nullable=True)
            entity_id = Column(String(80), ForeignKey("Entity.id"))
            activity_id = Column(String(80), ForeignKey("Activity.id"))

        # Agent

        class Agent(self.Base):
            __tablename__ = "Agent"
            id = Column(String(80), primary_key=True)
            name = Column(String(255))
            email = Column(String(255))

        class WasAssociatedWith(self.Base):
            __tablename__ = "WasAssociatedWith"
            id = Column(String(80), primary_key=True)
            role = Column(String(255), primary_key=True)
            activity_id = Column(
                String(80), ForeignKey("Activity.id"), primary_key=True
            )
            agent_id = Column(String(255), ForeignKey("Agent.id"), nullable=True)

        class WasAttributedTo(self.Base):
            __tablename__ = "WasAttributedTo"
            id = Column(String(80), primary_key=True)
            role = Column(String(255), primary_key=True)
            entity_id = Column(String(255), ForeignKey("Entity.id"), nullable=True)
            agent_id = Column(String(80), ForeignKey("Agent.id"), primary_key=True)

        # Connect DB

        # self.Base.prepare(self.engine, reflect=True)
        self.Base.metadata.create_all(self.engine)
        # link to tables
        self.Activity = Activity  # self.Base.classes.jobs
        self.Parameter = Parameter  # self.Base.classes.job_parameters
        self.Entity = Entity
        self.WasGeneratedBy = WasGeneratedBy
        self.Used = Used
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def __del__(self):
        self.session.close()
