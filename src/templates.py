from aiohttp import web


def html_response(document):
    s = open(document, "r")
    return web.Response(text=s.read(), content_type='text/html')
