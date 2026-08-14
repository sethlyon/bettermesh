import { Container } from "@cloudflare/containers";

export interface Env {
  BETTERMESH_CONTAINER: DurableObjectNamespace<BetterMeshContainer>;
  SESSION_SECRET: string;
  ANTHROPIC_API_KEY: string;
}

// One container instance for the whole app: the demo's SQLite store and
// session state need to live in a single process, not be sharded per request.
export class BetterMeshContainer extends Container<Env> {
  defaultPort = 8080;
  sleepAfter = "10m";

  envVars = {
    SESSION_SECRET: this.env.SESSION_SECRET,
    ANTHROPIC_API_KEY: this.env.ANTHROPIC_API_KEY ?? "",
  };
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const container = env.BETTERMESH_CONTAINER.getByName("primary");
    return container.fetch(request);
  },
};
