#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Those classes handle the storage of the job information on the server
(e.g. files, relational database, ...)

Specific functions are expected for a storage class to save and read job information:
* save
* read
* delete
* get_job_list

Rq: sometimes we need access to the job attributes only, not the parameters or results,
therefore it is possible to retrieve only attributes, parameters or results so as to limit
the number of database access (in the case of a relational database)
"""

import datetime as dt
#from entity_store import *
import hashlib
from .settings import *
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column
from sqlalchemy import ForeignKey, Float, String, Boolean, Integer, BigInteger, DateTime, Text
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.dialects import sqlite


# ---------
# Exceptions/Warnings


class NotFoundWarning(Warning):
    """Warning used if Storage does not contain the information"""
    pass


# ---------
# Storage classes


class JobStorage(object):
    """
    Manage job information storage. This class defines required functions executed
    by the UWS server save(), read(), delete()
    """

    def save(self, job, save_attributes=True, save_parameters=True, save_results=True):
        """Save job information to storage (attributes, parameters and results)"""
        pass

    def read(self, job, get_attributes=True, get_parameters=True, get_results=True,
             from_process_id=False):
        """Read job information from storage"""
        pass

    def delete(self, job):
        """Delete job information from storage"""
        pass

    def get_list(self, joblist, phase=None, where_owner=True):
        """Get job list from storage"""
        pass


class UserStorage(object):
    """
    Manage user information storage.
    """

    def get_users(self):
        """Get list of users with their token and roles"""
        pass

    def add_user(self, name, token, roles=''):
        """Add user"""
        pass

    def remove_user(self, name, token):
        """Remove user from storage"""
        pass

    def update_user(self, name, key, value):
        """Update user attribute"""
        pass

    def add_role(self, name, token, role=''):
        """Add role to user, i.e. access to a job"""
        pass

    def remove_role(self, name, token, role=''):
        """Get job list from storage, i.e. access to a job"""
        pass

    def has_role(self, name, token, role=''):
        """Check if user has role"""
        pass

    def has_access(self, user, jobname):
        """Check if user has access to the job"""
        pass


class EntityStorage(object):
    """
    Manage Entity storage.
    """

    def get_hash(self, path):
        """Generate SHA hash for given file
        :param fname:
        :return: hax hash
        """
        BUF_SIZE = 65536  # lets read stuff in 64kb chunks!
        sha = getattr(hashlib, 'sha' + SHA_ALGO)()
        with open(path, 'rb') as f:
            while True:
                data = f.read(BUF_SIZE)
                if not data:
                    break
                sha.update(data)
        return sha.hexdigest()

    def register_entity(self, jobid, file_name, file_url, file_dir=None, hash=None, owner='anonymous', owner_token='anonymous'):
        """Add entity, store hash and properties, return entity_id"""
        pass

    def remove_entity(self, entity_id, owner='anonymous', owner_token='anonymous'):
        """Remove entity"""
        pass

    def get_entity(self, entity_id):
        """Return all entity attributes"""
        pass

    def search_entity(self, entity_id=None, jobid=None, result_name=None, file_name=None, hash=None, owner='anonymous', owner_token='anonymous'):
        """Search entity, return all entity attributes, maybe for several entities"""
        pass


# ----------
# SQLAlchemy


class SQLAlchemyJobStorage(JobStorage, UserStorage, EntityStorage):

    def __init__(self, db_string=SQLALCHEMY_DB):
        self.engine = create_engine(db_string)  # , connect_args={'check_same_thread': False})
        self.Base = declarative_base()
        # self.Base = automap_base()
        # dt_format = u'%(year)04d/%(month)02d/%(day)02dT%(hour)02d:%(min)02d:%(second)02d'
        # dt_regexp = u'(\d+)/(\d+)/(\d+)T(\d+):(\d+):(\d+)'
        # myDateTime = DateTime().with_variant(sqlite.DATETIME(storage_format=dt_format, regexp=dt_regexp), 'sqlite')
        # myDateTime = DateTime().with_variant(sqlite.TIMESTAMP(), 'sqlite')
        if STORAGE_TYPE == 'SQLite':
            myDateTime = DateTime().with_variant(String(19), 'sqlite')
            myBoolean = Boolean().with_variant(String(5), 'sqlite')
        else:
            myDateTime = DateTime()
            myBoolean = Boolean()

        class Job(self.Base):
            __tablename__ = 'jobs'
            jobid = Column(String(80), primary_key=True)  # uuid: max=36
            jobname = Column(String(255))
            phase = Column(String(10))
            quote = Column(Integer(), nullable=True)
            execution_duration = Column(Integer(), nullable=True)
            error = Column(Text(), nullable=True)
            creation_time = Column(myDateTime)
            start_time = Column(myDateTime, nullable=True)
            end_time = Column(myDateTime, nullable=True)
            destruction_time = Column(myDateTime, nullable=True)
            owner = Column(String(64), nullable=True)
            owner_token = Column(String(128), nullable=True)
            run_id = Column(String(64), nullable=True)
            process_id = Column(BigInteger(), nullable=True)

        class Parameter(self.Base):
            __tablename__ = 'job_parameters'
            jobid = Column(String(80), ForeignKey("jobs.jobid"), primary_key=True)  # uuid: max=36
            name = Column(String(255), primary_key=True)
            value = Column(String(255), nullable=True)
            byref = Column(myBoolean, default=False, nullable=True)
            # from_entity = Column(myBoolean, default=False, nullable=True)
            entity_id = Column(String(255), ForeignKey("entities.entity_id"), nullable=True)

        class Result(self.Base):
            __tablename__ = 'job_results'
            jobid = Column(String(80), ForeignKey("jobs.jobid"), primary_key=True)  # uuid: max=36
            name = Column(String(255), primary_key=True)
            url = Column(String(255), nullable=True)
            content_type = Column(String(64), nullable=True)
            entity_id = Column(String(255), ForeignKey("entities.entity_id"), nullable=True)

        class User(self.Base):
            __tablename__ = 'users'
            name = Column(String(80), primary_key=True)
            token = Column(String(255), default=TOKEN_GEN)
            roles = Column(String(255), default='')
            active = Column(Boolean(), default=True)
            first_connection = Column(myDateTime)
            # last_login = Column(myDateTime)
            # TODO: add last_connection, ips?,
            # TODO: roles as a table with FK to jobnames,

        class Entity(self.Base):
            __tablename__ = 'entities'
            entity_id = Column(String(80), primary_key=True)
            value = Column(String(255), nullable=True)
            file_name = Column(String(255), nullable=True)
            file_dir = Column(String(255), nullable=True)
            hash = Column(String(255), nullable=True)
            # hash_type = Column(String(255), nullable=True)
            creation_time = Column(myDateTime)
            content_type = Column(String(255), nullable=True)
            access_url = Column(String(255), nullable=True)
            owner = Column(String(64))
            # was generated by:
            jobid = Column(String(80), ForeignKey("jobs.jobid"), nullable=True)  # uuid: max=36
            result_name = Column(String(255), nullable=True)
            result_value = Column(String(255), nullable=True)
            # derivation
            from_entity = Column(String(80), nullable=True)

        class Used(self.Base):
            __tablename__ = 'used'
            entity_id = Column(String(80), ForeignKey("entities.entity_id"), primary_key=True)
            jobid = Column(String(80), ForeignKey("jobs.jobid"), primary_key=True)  # uuid: max=36
            role = Column(String(255), nullable=True)
            owner = Column(String(64), nullable=True)

        # self.Base.prepare(self.engine, reflect=True)
        self.Base.metadata.create_all(self.engine)
        self.Job = Job  # self.Base.classes.jobs
        self.Parameter = Parameter  # self.Base.classes.job_parameters
        self.Result = Result  # self.Base.classes.job_results
        self.User = User
        self.Entity = Entity
        self.Used = Used
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def __del__(self):
        self.session.close()

    # ----------
    # UserStorage methods

    def get_users(self, name=None):
        """Get list of users with their token and roles"""
        if name:
            rows = self.session.query(self.User).filter_by(name=name).all()
        else:
            rows = self.session.query(self.User).all()
        users = [r.__dict__ for r in rows]
        return users

    def add_user(self, name, token=None, roles=None):
        """Add user"""
        row = self.session.query(self.User).filter_by(name=name).first()
        if not row:
            d = {
                'name': name,
                'first_connection': dt.datetime.now(),
            }
            if token:
                d['token'] = token
            if roles:
                d['roles'] = roles
            u = self.User(**d)
            self.session.merge(u)
            self.session.commit()
            logger.info('User {} added to db'.format(name))
        # else:
        #     logger.info('User {} already exists in db'.format(name))

    def remove_user(self, name):
        """Remove user from storage"""
        self.session.query(self.User).filter_by(name=name).delete()
        self.session.commit()
        logger.info('User {} removed from db'.format(name))

    def update_user(self, name, key, value):
        """Update user attribute"""
        row = self.session.query(self.User).filter_by(name=name).first()
        setattr(row, key, value)
        self.session.commit()
        logger.debug('User {} updated: {}={}'.format(name, key, value))

    def get_roles(self, user):
        row = self.session.query(self.User).filter_by(name=user.name, token=user.token).first()
        roles = []
        if row:
            roles = row.roles.split(',')
        return roles

    def add_role(self, name, token, role=''):
        """Add role to user, i.e. access to a job"""
        row = self.session.query(self.User).filter_by(name=name, token=token).first()
        roles = row.roles.split(',')
        if not role in roles:
            roles.append(role)
            row.roles = ','.join(roles)
            self.session.merge(row)
            self.session.commit()
            logger.debug('Role {} added for user {}'.format(role, name))
        else:
            logger.debug('Role {} already set for user {}'.format(role, name))

    def remove_role(self, name, token, role=''):
        """Get job list from storage, i.e. access to a job"""
        row = self.session.query(self.User).filter_by(name=name, token=token).first()
        roles = row.roles.split(',')
        if role in roles:
            roles.pop(role)
            row.roles = ','.join(roles)
            self.session.merge(row)
            self.session.commit()
            logger.debug('Role {} removed for user {}'.format(role, name))
        else:
            logger.debug('Role {} not found for user {}'.format(role, name))

    def has_role(self, name, token, role=''):
        row = self.session.query(self.User).filter_by(name=name, token=token).first()
        if row:
            roles = row.roles.split(',')
            if ('all' in roles) or (role in roles):
                # logger.debug('Role \"{}\" ok for user {}:{}'.format(role, name, token))
                return True
            else:
                logger.debug('Role \"{}\" not found for user {}'.format(role, name))
                return False

    def has_access(self, user, jobname):
        """Check if user has access to the job, i.e that job is in list of roles"""
        if user.check_admin():
            return True
        return self.has_role(user.name, user.token, role=jobname)

    # ----------
    # JobStorage methods

    def _save_parameter(self, job, pname):
        # Save job parameter to db
        eid = job.parameters[pname]['entity_id']
        if not eid or eid == '0':
            eid = None
        d = {
            'jobid': job.jobid,
            'name': pname,
            'value': job.parameters[pname]['value'],
            'byref': job.parameters[pname]['byref'],
            'entity_id': eid,
        }
        p = self.Parameter(**d)
        self.session.merge(p)

    def _save_result(self, job, rname):
        # Save job result to db
        d = {
            'jobid': job.jobid,
            'name': rname,
            'url': job.results[rname]['url'],
            'content_type': job.results[rname]['content_type'],
            'entity_id': job.results[rname]['entity_id'],
        }
        r = self.Result(**d)
        self.session.merge(r)

    def save(self, job, save_attributes=True, save_parameters=True, save_results=True):
        """Save job information to storage (attributes, parameters and results)"""
        if save_attributes:
            # Save job description to db
            d = {col: job.__dict__[col] for col in JOB_ATTRIBUTES}
            j = self.Job(**d)
            self.session.merge(j)
            self.session.commit()
        if save_parameters:
            if isinstance(save_parameters, str):
                # Save the given job parameter to db
                pname = save_parameters
                self._save_parameter(job, pname)
                self.session.commit()
            else:
                # Save all job parameters to db
                for pname in list(job.parameters.keys()):
                    self._save_parameter(job, pname)
                self.session.commit()
        if save_results:
            # Save job results to db
            for rname in list(job.results.keys()):
                self._save_result(job, rname)
            self.session.commit()

    def read(self, job, get_attributes=True, get_parameters=True, get_results=True,
             from_process_id=False):
        """Read job information from storage"""
        if get_attributes:
            if from_process_id:
                # Query db for jobname and jobid using process_id
                row = self.session.query(self.Job).filter_by(process_id=job.process_id).first()
                if not row:
                    raise NotFoundWarning('Job with process_id={} NOT FOUND'.format(job.process_id))
                # job.jobname = row.jobname
                # job.jobid = row.jobid
            else:
                row = self.session.query(self.Job).filter_by(jobid=job.jobid).first()
                if not row:
                    raise NotFoundWarning('Job "{}" NOT FOUND'.format(job.jobid))
            for k in JOB_ATTRIBUTES:
                if k in list(row.__dict__.keys()):
                    job.__dict__[k] = row.__dict__[k]
        if get_parameters:
            # Query db for job parameters
            params = self.session.query(self.Parameter).filter_by(jobid=job.jobid).all()
            # Format results to a parameter dict
            params_dict = {
                row.name: {
                    'value': row.value,
                    'byref': row.byref,
                    'entity_id': row.entity_id,
                }
                for row in params
            }
            job.parameters = params_dict
        else:
            job.parameters = {}
        if get_results:
            # Query db for job results
            results = self.session.query(self.Result).filter_by(jobid=job.jobid).all()
            results_dict = {}
            for rrow in results:
                rrow_dict = {
                    'url': rrow.url,
                    'content_type': rrow.content_type,
                    'entity_id': rrow.entity_id,
                }
                entity = self.session.query(self.Entity).filter_by(entity_id=rrow.entity_id).first()
                if entity:
                    logger.debug(entity)
                    rrow_dict['file_name'] = entity.entity_id + '_' + entity.file_name
                    rrow_dict['hash'] = entity.hash
                results_dict[rrow.name] = rrow_dict
            job.results = results_dict
        else:
            job.results = {}

    def delete(self, job):
        """Delete job information from storage"""
        self.session.query(self.Parameter).filter_by(jobid=job.jobid).delete()
        self.session.query(self.Result).filter_by(jobid=job.jobid).delete()
        self.session.query(self.Job).filter_by(jobid=job.jobid).delete()
        self.session.commit()

    def get_list(self, joblist, phase=None, after=None, last=None, where_owner=True):
        """Get job list from storage"""
        query = self.session.query(self.Job).filter_by(jobname=joblist.jobname)
        if phase:
            query = query.filter(self.Job.phase.in_(phase))
        else:
            query = query.filter(self.Job.phase.notin_(["ARCHIVED"]))
        if after:
            query = query.filter(self.Job.creation_time >= after)
        if where_owner:
            query = query.filter_by(owner=joblist.user.name)
            query = query.filter_by(owner_token=joblist.user.token)
        query = query.order_by(self.Job.creation_time.asc())
        if last:
            query = query.limit(last)
        jobs = query.all()
        djobs = [job.__dict__ for job in jobs]
        return djobs

    # ----------
    # EntityStorage methods

    def register_entity(self, **kwargs):
        # jobid, result_name, file_name, file_dir=None, access_url=None, hash=None, content_type=None,
        # owner='anonymous', owner_token='anonymous'):
        """Find or add entity, store hash and properties, return entity_id"""
        entity = {}
        # Check for required attributes in kwargs
        # for k in ['owner']:
        #     if not k in kwargs:
        #         raise UserWarning('Attribute {} is missing to register an entity'.format(k))

        # Files
        if 'file_name' in kwargs:
            if not 'file_dir' in kwargs:
                logger.warning('No file_dir given for file entity: {}'.format(kwargs))
                kwargs['file_dir'] = '.'
            # Redefine file_dir if ARCHIVE is Local (the generated file has been copied to RESULTS_PATH)
            if ARCHIVE == 'Local':
                if 'result_name' in kwargs:
                    kwargs['file_dir'] = os.path.join(RESULTS_PATH, kwargs['jobid'])
                elif 'used_jobid' in kwargs:
                    kwargs['file_dir'] = os.path.join(UPLOADS_PATH, kwargs['used_jobid'])
            # Compute hash if not given (look for file in file_dir)
            if 'hash' not in kwargs:
                full_path = os.path.join(kwargs['file_dir'], kwargs['file_name'])
                if os.path.isfile(full_path):
                    kwargs['hash'] = self.get_hash(full_path)

            # Check if file already exists --> first hash, then test if filename contains entity_id or jobid if found
            if 'hash' in kwargs:
                elist = self.session.query(self.Entity).filter_by(hash=kwargs['hash']).all()
                if elist:
                    for row in elist:
                        if str(row.entity_id) in kwargs['file_name']:
                            # Entity has the expected entity_id in its name
                            entity = dict((col, getattr(row, col)) for col in row.__table__.columns.keys())
                            entity_id = entity['entity_id']
                            logger.info('Entity found for {} with same hash, and file_name contains entity_id'.format(
                                kwargs['file_name']))
                        elif 'jobid' in kwargs and str(row.jobid) == str(kwargs.get('jobid')):
                            # Entity has the jobid that generated it in its name
                            entity = dict((col, getattr(row, col)) for col in row.__table__.columns.keys())
                            entity_id = entity['entity_id']
                            logger.info('Entity found for {} with same hash, and file_name contains jobid'.format(
                                kwargs['file_name']))
                        elif str(row.jobid) in kwargs['file_name']:
                            # Entity has the jobid that generated it in its name
                            entity = dict((col, getattr(row, col)) for col in row.__table__.columns.keys())
                            entity_id = entity['entity_id']
                            logger.info('Entity found for {} with same hash, and file_name contains jobid'.format(
                                kwargs['file_name']))
                        else:
                            used = self.session.query(self.Used).filter_by(entity_id=row.entity_id, jobid=kwargs.get(
                                'jobid')).first()
                            if used and (getattr(row, 'file_name') == kwargs['file_name']):
                                # Entity has already been used by the same job (and is now exposed as a UWS result)
                                entity = dict((col, getattr(row, col)) for col in row.__table__.columns.keys())
                                entity_id = entity['entity_id']
                                logger.info('Entity found for {} with same hash, was used by the same job and is now exposed as a UWS result'.format(kwargs['file_name']))

        # Value (may be an identifier)
        if 'value' in kwargs:
            for k in ['name']:
                if not k in kwargs:
                    raise UserWarning('Attribute {} is missing to register an entity'.format(k))
            # entity is a value or an ID
            row = self.session.query(self.Entity).filter_by(entity_id=kwargs['value']).first()
            if row:
                entity_id = kwargs['value']
                entity = dict((col, getattr(row, col)) for col in row.__table__.columns.keys())
                logger.info('Entity found with value=entity_id={}'.format(entity_id))
            else:
                # Not found in entity store, is it an entity_id or a simple value ?
                pass

        # Unknown entity, use existing entity_id or generate a new one
        if not entity:
            if 'entity_id' in kwargs:
                # Store given identifier for the new entity
                row = self.session.query(self.Entity).filter_by(entity_id=entity_id).first()
                if row:
                    entity = dict((col, getattr(row, col)) for col in row.__table__.columns.keys())
                    logger.info('Entity found from given entity_id={}'.format(entity_id))
            else:
                # Generate unique identifier for the new entity
                entity_id = ENTITY_ID_GEN(**kwargs)

        # Check if entity is being used (pop used_jobid and used_role and add Used entry)
        if 'used_jobid' in kwargs:
            jobid = kwargs.pop('used_jobid')
            role = kwargs.pop('used_role', None)
            used = self.Used(entity_id=entity_id, jobid=jobid, role=role, owner=kwargs['owner'])
            self.session.merge(used)
            self.session.commit()
            logger.info('Adding Used relation for file_name={} (entity_id={}, jobid={})'.format(kwargs['file_name'], entity_id, jobid))

        # Register new entity
        if not entity:
            # Store new entity and return attributes
            kwargs['entity_id'] = entity_id
            # Define access_url if not given
            if not 'access_url' in kwargs:
                url = ARCHIVE_URL.format(ID=entity_id)
                if url.startswith('/'):
                    url = '{}{}'.format(BASE_URL, url)
                kwargs['access_url'] = url
            # Store info in DB
            e = self.Entity(**kwargs)
            self.session.merge(e)
            self.session.commit()
            # Return entity attributes
            logger.info('New entity registered: {}'.format(str(kwargs)))
            return kwargs
        else:
            # Return existing entity attributes
            logger.info('Existing entity found: {}'.format(str(entity)))
            # TODO: update entity with kwargs?
            return entity

    def remove_entity(self, entity_id=None, jobid=None, owner='anonymous'):
        """Remove entity"""
        if entity_id:
            self.session.query(self.Entity).filter_by(entity_id=entity_id).delete()
            self.session.query(self.Used).filter_by(entity_id=entity_id).delete()
        elif jobid:
            self.session.query(self.Entity).filter_by(jobid=jobid).delete()
            self.session.query(self.Used).filter_by(jobid=jobid).delete()
        self.session.commit()

    def get_entity(self, entity_id, silent=False):
        """Return all entity attributes"""
        query = self.session.query(self.Entity).filter_by(entity_id=entity_id)
        row = query.first()
        if not row:
            if silent:
                return {}
            else:
                raise NotFoundWarning('Result "{}" NOT FOUND'.format(entity_id))
        return dict((col, getattr(row, col)) for col in row.__table__.columns.keys())

    def search_entity(self, entity_id=None, jobid=None, result_name=None, file_name=None, hash=None, owner='anonymous', owner_token='anonymous'):
        """Search entity, return all entity attributes, maybe for several entities"""
        if entity_id:
            return self.get_entity(entity_id, silent=True)
        elif jobid and result_name:
            query = self.session.query(self.Entity).filter_by(jobid=jobid, result_name=result_name)
            row = query.first()
            if not row:
                raise NotFoundWarning('Entity with jobid={} and result_name={} NOT FOUND'.format(jobid, result_name))
            return dict((col, getattr(row, col)) for col in row.__table__.columns.keys())
        elif file_name and hash:
            query = self.session.query(self.Entity).filter_by(file_name=file_name, hash=hash)
            row = query.first()
            if not row:
                raise NotFoundWarning('Entity with file_name={} and hash={} NOT FOUND'.format(file_name, hash))
            return dict((col, getattr(row, col)) for col in row.__table__.columns.keys())
        elif hash:
            query = self.session.query(self.Entity).filter_by(hash=hash)
            row = query.first()
            if not row:
                raise NotFoundWarning('Entity with hash={} NOT FOUND'.format(hash))
            return dict((col, getattr(row, col)) for col in row.__table__.columns.keys())
        else:
            pass
        pass



# ----------
# TO BE REMOVED...

# ----------
# SQL


class SQLStorage(object):
    """Manage job information storage using SQL database

    This class defines required functions executed by the UWS server:
    save(), read(), delete()
    """

    # connector and cursor to be initialized by subclass
    conn = None
    cursor = None

    def _save_query(self, table_name, d):
        query = "INSERT OR REPLACE INTO {} ({}) VALUES ('{}')" \
                "".format(table_name, ", ".join(list(d.keys())), "', '".join(map(str, list(d.values()))))
        query = query.replace("'None'", "NULL")
        self.cursor.execute(query)
        self.conn.commit()


class SQLJobStorage(SQLStorage, JobStorage):
    """Manage job information storage using SQL database

    This class defines required functions executed by the UWS server:
    save(), read(), delete()
    """

    def _save_parameter(self, job, pname):
        # Save job parameter to db
        d = {
            'jobid': job.jobid,
            'name': pname,
            'value': job.parameters[pname]['value'],
            'byref': job.parameters[pname]['byref'],
            'entity_id': job.parameters[pname]['entity_id'],
        }
        self._save_query('job_parameters', d)

    def _save_result(self, job, rname):
        # Save job parameter to db
        d = {
            'jobid': job.jobid,
            'name': rname,
            'url': job.results[rname]['url'],
            'content_type': job.results[rname]['content_type'],
            'entity_id': job.results[rname]['entity_id'],
        }
        self._save_query('job_results', d)

    def save(self, job, save_attributes=True, save_parameters=False, save_results=False):
        """Save job information to storage (attributes, parameters and results)"""
        if save_attributes:
            # Save job description to db
            d = {col: str(job.__dict__[col]) for col in JOB_ATTRIBUTES}
            self._save_query('jobs', d)
        if save_parameters:
            if isinstance(save_parameters, str):
                # Save the given job parameter to db
                pname = save_parameters
                self._save_parameter(job, pname)
            else:
                # Save all job parameters to db
                logger.info(str(job.parameters.keys()))
                for pname in list(job.parameters.keys()):
                    self._save_parameter(job, pname)
        if save_results:
            # Save job results to db
            for rname in list(job.results.keys()):
                self._save_result(job, rname)

    # noinspection PyTypeChecker
    def read(self, job, get_attributes=True, get_parameters=False, get_results=False, from_process_id=False):
        """Read job from storage"""
        if from_process_id:
            # Query db for jobname and jobid using process_id
            query = "SELECT jobname, jobid FROM jobs WHERE process_id='{}';".format(job.process_id)
            row = self.cursor.execute(query).fetchone()
            if not row:
                raise NotFoundWarning('Job with process_id={} NOT FOUND'.format(job.process_id))
            job.jobname = row['jobname']
            job.jobid = row['jobid']
        if get_attributes:
            # Query db for job description
            query = "SELECT * FROM jobs WHERE jobid='{}';".format(job.jobid)
            row = self.cursor.execute(query).fetchone()
            if not row:
                raise NotFoundWarning('Job "{}" NOT FOUND'.format(job.jobid))
            # creation_time = dt.datetime.strptime(job['creation_time'], DT_FMT)
            # start_time = dt.datetime.strptime(row['start_time'], DT_FMT)
            # end_time = dt.datetime.strptime(row['end_time'], DT_FMT)
            # destruction_time = dt.datetime.strptime(row['destruction_time'], DT_FMT)
            job.jobname = row['jobname']
            job.phase = row['phase']
            job.quote = row['quote']
            job.execution_duration = row['execution_duration']
            job.error = row['error']
            job.creation_time = row['creation_time']  # creation_time.strftime(DT_FMT)
            job.start_time = row['start_time']  # start_time.strftime(DT_FMT)
            job.end_time = row['end_time']  # end_time.strftime(DT_FMT)
            job.destruction_time = row['destruction_time']  # destruction_time.strftime(DT_FMT)
            job.owner = row['owner']
            job.owner_token = row['owner_token']
            job.run_id = row['run_id']
            job.process_id = row['process_id']
        if get_parameters:
            # Query db for job parameters
            query = "SELECT * FROM job_parameters WHERE jobid='{}';".format(job.jobid)
            params = self.cursor.execute(query).fetchall()
            # Format results to a parameter dict
            params_dict = {
                row['name']: {
                    'value': row['value'],
                    'byref': row['byref']
                }
                for row in params
            }
            job.parameters = params_dict
        else:
            job.parameters = {}
        if get_results:
            # Query db for job results
            query = "SELECT * FROM job_results WHERE jobid='{}';".format(job.jobid)
            results = self.cursor.execute(query).fetchall()
            results_dict = {
                row['name']: {
                    'url': row['url'],
                    'content_type': row['content_type']
                }
                for row in results
            }
            job.results = results_dict
        else:
            job.results = {}

    def delete(self, job):
        """Delete job from storage"""
        query1 = "DELETE FROM job_results WHERE jobid='{}';".format(job.jobid)
        self.cursor.execute(query1)
        query2 = "DELETE FROM job_parameters WHERE jobid='{}';".format(job.jobid)
        self.cursor.execute(query2)
        query3 = "DELETE FROM jobs WHERE jobid='{}';".format(job.jobid)
        self.cursor.execute(query3)
        self.conn.commit()

    def get_list(self, joblist, phase=None, after=None, last=None, where_owner=True):
        """Query storage for job list"""
        query = "SELECT jobid, phase FROM jobs"
        where = ["jobname='{}'".format(joblist.jobname)]
        if phase:
            where_phase = []
            for p in phase:
                where_phase.append("phase='{}'".format(p))
            where.append('({})'.format(" OR ".join(where_phase)))
        if where_owner:
            where.append("owner='{}'".format(joblist.user.name))
            where.append("owner_token='{}'".format(joblist.user.token))
        query += " WHERE " + " AND ".join(where)
        query += " ORDER BY destruction_time ASC"
        logger.debug('query = {}'.format(query))
        jobs = self.cursor.execute(query).fetchall()
        return jobs


# ----------
# SQLite


class SQLiteStorage(object):
    """Manage job information storage using SQLite"""

    def __init__(self, db_file=SQLITE_FILE):
        # Get connector to db_file

        import sqlite3

        def dict_factory(cursor, row):
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d

        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = dict_factory  # sqlite3.Row  #
        self.cursor = self.conn.cursor()

    def __del__(self):
        self.cursor.close()
        self.conn.close()


class SQLiteJobStorage(SQLiteStorage, SQLJobStorage):
    pass


# ----------
# PostgreSQL


class PostgreSQLStorage(object):
    """Manage job information storage using PostgreSQL"""

    def __init__(self, host=PGSQL_HOST, port=PGSQL_PORT, database=PGSQL_DATABASE,
                 user=PGSQL_USER, password=PGSQL_PASSWORD):
        # Get connector to db_file
        import psycopg2
        import psycopg2.extras
        self.conn = psycopg2.connect(host=host, port=port, database=database,
                                     user=user, password=password)
        self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    def __del__(self):
        self.cursor.close()
        self.conn.close()


class PostgreSQLJobStorage(PostgreSQLStorage, SQLJobStorage):
    pass
