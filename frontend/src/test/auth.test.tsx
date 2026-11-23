import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { LoginPage, RegisterPage } from "../pages/AuthPages";
import { renderApp } from "./utils";

vi.mock("../api", async (orig) => ({ ...(await orig<typeof import("../api")>()), authApi: { providers: vi.fn().mockResolvedValue({ google: false }) } }));

describe("Login", () => {
  it("validates required fields", async () => {
    renderApp(<LoginPage />, { auth: { user: null } });
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByText("Email is required")).toBeInTheDocument();
    expect(screen.getByText("Password is required")).toBeInTheDocument();
  });
  it("submits credentials to the auth context", async () => {
    const login = vi.fn().mockResolvedValue(undefined);
    renderApp(<LoginPage />, { auth: { user: null, login } });
    await userEvent.type(screen.getByLabelText("Email"), "a@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "password123");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    await waitFor(() => expect(login).toHaveBeenCalledWith("a@example.com", "password123"));
  });
  it("shows the server's error message and no success", async () => {
    const login = vi.fn().mockRejectedValue(new Error("Invalid email or password"));
    renderApp(<LoginPage />, { auth: { user: null, login } });
    await userEvent.type(screen.getByLabelText("Email"), "a@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password");
  });
  it("says plainly when Google login is not configured", async () => {
    renderApp(<LoginPage />, { auth: { user: null } });
    expect(await screen.findByText(/Google login is not configured/)).toBeInTheDocument();
  });
});

describe("Register", () => {
  it("rejects short passwords and bad emails", async () => {
    const register = vi.fn();
    renderApp(<RegisterPage />, { auth: { user: null, register } });
    await userEvent.type(screen.getByLabelText("Email"), "not-an-email");
    await userEvent.type(screen.getByLabelText("Password"), "short");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByText("Enter a valid email")).toBeInTheDocument();
    expect(screen.getByText("Use at least 8 characters")).toBeInTheDocument();
    expect(register).not.toHaveBeenCalled();
  });
  it("registers with valid input", async () => {
    const register = vi.fn().mockResolvedValue(undefined);
    renderApp(<RegisterPage />, { auth: { user: null, register } });
    await userEvent.type(screen.getByLabelText("Name"), "Alex");
    await userEvent.type(screen.getByLabelText("Email"), "a@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "password123");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));
    await waitFor(() => expect(register).toHaveBeenCalledWith("a@example.com", "password123", "Alex"));
  });
});
