import { Container } from "@cloudflare/containers";

export interface Env {
  BETTERMESH_CONTAINER: DurableObjectNamespace<BetterMeshContainer>;
  SESSION_SECRET: string;
  WEBHOOK_SECRET: string;
}

// One container instance for the whole app: the demo's SQLite store and
// session state need to live in a single process, not be sharded per request.
// Every hospice's custom domain (bettermesh/anchorpoint/cedarridge/thistlemoor
// .theslyon.com) routes to this same container — the app itself branches on
// the Host header, not on separate deployments.
export class BetterMeshContainer extends Container<Env> {
  defaultPort = 8080;
  sleepAfter = "10m";

  envVars = {
    SESSION_SECRET: this.env.SESSION_SECRET,
    WEBHOOK_SECRET: this.env.WEBHOOK_SECRET,
  };
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const container = env.BETTERMESH_CONTAINER.getByName("primary");
    return container.fetch(request);
  },
};
