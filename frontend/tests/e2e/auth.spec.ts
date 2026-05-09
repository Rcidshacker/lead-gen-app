"""LeadForge frontend E2E tests using Playwright.

These tests mock the backend API responses using Playwright's
route interception to ensure UI tests are deterministic and
don't require a populated database.
"""


async def test_login_page_renders(page):
    """Login page should render the email and password inputs."""
    await page.goto("/login")

    email_input = page.locator('input[type="email"], input[name="email"]')
    password_input = page.locator('input[type="password"]')

    await email_input.wait_for(timeout=5000)
    await password_input.wait_for(timeout=5000)

    assert await email_input.is_visible()
    assert await password_input.is_visible()


async def test_dashboard_requires_auth(page):
    """Visiting /dashboard without auth should redirect to /login."""
    await page.route("**/api/v1/**", lambda route: route.fulfill(
        status=401,
        content='{"detail": "Not authenticated"}',
        headers={"Content-Type": "application/json"},
    ))

    await page.goto("/dashboard")
    current_url = page.url
    assert "/login" in current_url or await page.locator('input[name="email"]').is_visible()


async def test_register_page_renders(page):
    """Register page should show name, email, and password fields."""
    await page.goto("/register")

    name_input = page.locator('input[name="full_name"], input[name="name"]')
    email_input = page.locator('input[type="email"], input[name="email"]')
    password_input = page.locator('input[type="password"]')

    await name_input.wait_for(timeout=5000)

    assert await name_input.is_visible()
    assert await email_input.is_visible()
    assert await password_input.is_visible()
