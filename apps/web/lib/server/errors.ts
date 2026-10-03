export class ApiError extends Error {
  constructor(public readonly status: number, public readonly code: string, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export function invalid(message: string): never {
  throw new ApiError(400, "INVALID_QUERY", message);
}
