import { ExecutionContext } from '@cloudflare/workers-types';

interface Env {
  ASSETS: { fetch: (request: Request | URL | string) => Promise<Response> };
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    
    // Check if the request is for a file (has an extension)
    // If it is, and we reached the worker, it means the asset wasn't found (if run_worker_first=false)
    // or we are just handling it. 
    // However, if run_worker_first=false (default for Assets), the worker is ONLY called if no asset matches.
    // So for SPA, we just need to return index.html for non-file routes.

    if (!url.pathname.match(/\.[^/]+$/)) {
      // Serve index.html for routes like /dashboard, /user/1, etc.
      return env.ASSETS.fetch(new URL('/index.html', request.url));
    }

    return new Response("Not Found", { status: 404 });
  },
};
