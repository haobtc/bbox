import uuid
import logging
import json
import asyncio
from aiohttp import web
from urllib.parse import urlparse, parse_qs

from aiobbox.jsonrpc import Request
from aiobbox.utils import json_to_str, get_ssl_context, localbox_ip
from aiobbox.cluster import get_cluster, get_box
from aiobbox.client import DEFAULT_TIMEOUT_SECS
from aiobbox.client import pool as srv_pool

from .pool import get_pool

logger = logging.getLogger('redistunnel')

class RedisTunnel:
    ssl_context = None
    def __init__(self, tunnel_url):
        self.parsed = urlparse(tunnel_url)
        if self.parsed.query:
            qs = parse_qs(self.parsed.query)
            certs = qs.get('ssl')
            if certs:
                self.ssl_context = get_ssl_context(certs[0])
        assert self.parsed.path and self.parsed.path.startswith('/')
        self.req_key = self.parsed.path[1:]

    @property
    def redis_url(self):
        return 'redis://{}'.format(self.parsed.netloc)

    async def get_redis_pool(self):
        return await get_pool(
            self.redis_url,
            ssl=self.ssl_context)

    async def request(self, srv, method, *params, req_id=None, timeout=DEFAULT_TIMEOUT_SECS):
        if req_id is None:
            req_id = uuid.uuid4().hex
        req = Request.make(req_id, srv, method, *params)
        return await self.request_obj(req, timeout=timeout)

    async def request_obj(self, req, timeout=DEFAULT_TIMEOUT_SECS):
        tmp_req_id = uuid.uuid4().hex
        payload = req.as_json()
        timeout = int(timeout)
        payload['id'] = tmp_req_id
        payload['timeout'] = timeout

        redis_pool = await self.get_redis_pool()
        await redis_pool.execute('LPUSH',
                                 self.req_key,
                                 json_to_str(payload))
        # wait for response
        res_key = 'tunnel.res.{}'.format(tmp_req_id)
        # TODO: timeout
        r = await redis_pool.execute(
            'BRPOP', res_key, timeout)
        if r is not None:
            key, res = r
            res = json.loads(res)
            res['id'] = req.req_id
            return res
        else:
            raise asyncio.TimeoutError from None

    async def take_jobs(self, whitelist=None, parallel=False):
        self.whitelist = whitelist
        redis_pool = await self.get_redis_pool()
        while get_cluster().is_running():
            key, body = await redis_pool.execute(
                'BRPOP', self.req_key, 0)
            logging.debug('brpoped %s %s', key, body)
            body = json.loads(body)
            if parallel:
                asyncio.ensure_future(self.handle_req(body))
            else:
                await self.handle_req(body)

    async def handle_req(self, body):
        req = Request(body)
        timeout = int(body.get(
            'timeout',
            DEFAULT_TIMEOUT_SECS))
        if not req.allowed(self.whitelist):
            res = req.error_response('method not allowed').as_json()
            return await self.respond(res, req, timeout)

        try:
            res = await srv_pool.request_obj(
                req,
                timeout=timeout)
            return await self.respond(res, req, timeout)
        except asyncio.TimeoutError:
            logger.warn('proxy request %s timeout', req.full_method, exc_info=True)
            res = req.error_response(
                {'code': 'timeout',
                 'message': 'request {} timeout'.format(req.full_method)}).as_json()
            return await self.respond(res, req, timeout)

    async def respond(self, res, req, timeout):
        redis_pool = await self.get_redis_pool()
        if req.req_id:
            res_key = 'tunnel.res.{}'.format(req.req_id)
            await redis_pool.execute('LPUSH', res_key, json_to_str(res))
            await redis_pool.execute('EXPIRE', res_key, timeout)

    async def start_proxy_server(self, args):
        boxid = args.boxid
        ssl_context = get_ssl_context(args.ssl)

        # server etcd agent
        curr_box = get_box()
        curr_box.ssl_prefix = args.ssl
        srv_names = args.srv_name
        await curr_box.start(boxid, srv_names)

        app = web.Application()
        app.router.add_post('/jsonrpc/2.0/api', self.proxy_requests)
        host, port = curr_box.bind.split(':')
        if not localbox_ip(host):
            host = '0.0.0.0'
        logger.warn('box {} launched as {}'.format(
            curr_box.boxid,
            curr_box.bind))
        handler = app.make_handler()
        loop = asyncio.get_event_loop()
        srv = await loop.create_server(
            handler,
            host, port,
            ssl=ssl_context)
        return srv, handler

    async def proxy_requests(self, request):
        try:
            body = await request.json()
            req = Request(body)

            timeout = float(request.headers.get('X-Bbox-Expect-Timeout', DEFAULT_TIMEOUT_SECS))
            timeout = max(min(timeout, 200), 0)

            if req.srv_name.startswith('proxy.'):
                req.srv_name = req.srv_name[len('proxy.'):]
            try:
                resp = await self.request_obj(req, timeout=timeout)
                return web.json_response(resp)
            except asyncio.CancelledError:
                logger.info('proxy request %s cancelled', req.full_method)
                err = req.error_response({'code': 'cancelled'})
                return web.json_response(err.as_json())
            except asyncio.TimeoutError:
                logger.info('proxy request %s timeout', req.full_method)
                err = req.error_response(
                    {'code': 'timeout',
                     'message': 'request {} timeout'.format(req.full_method)})
                return web.json_response(err.as_json())
        except:
            logger.error('proxy requests error', exc_info=True)
            raise
