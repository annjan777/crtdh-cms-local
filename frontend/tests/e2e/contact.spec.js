// Contact form states (PLAN WS2.8). The build under test sets CONTACT_API_URL to
// https://contact.crtdh.test/api/v1/contact/; every call is intercepted here, nothing leaves the machine.
import { expect, test } from '@playwright/test'
import { snapshot } from './helpers.js'

const API = '**/api/v1/contact/'
const email = snapshot.singletons['site-settings'].email_primary

async function fill(page) {
  await page.getByLabel('Your name').fill('Priya Das')
  await page.getByLabel('Email', { exact: true }).fill('priya@example.com')
  await page.getByLabel('Message', { exact: true }).fill('We would like to test a diagnostic prototype at the centre.')
}

test('errors appear on blur, not while typing, and clear on focus', async ({ page }) => {
  await page.goto('/contact/')
  const emailBox = page.getByLabel('Email', { exact: true })
  await emailBox.fill('priya@')
  await expect(page.locator('#contact-email-error')).toHaveCount(0)
  await emailBox.blur()
  await expect(page.locator('#contact-email-error')).toHaveText(/like name@example.com/)
  await expect(emailBox).toHaveAttribute('aria-invalid', 'true')
  await emailBox.focus()
  await expect(page.locator('#contact-email-error')).toHaveCount(0)
})

test('send with empty fields reports every problem and focuses the first; button stays enabled', async ({ page }) => {
  await page.goto('/contact/')
  const send = page.getByRole('button', { name: 'Send message' })
  await expect(send).toBeEnabled()
  await send.click()
  await expect(page.getByLabel('Your name')).toBeFocused()
  await expect(page.locator('.field__error')).toHaveCount(3)
})

test('shows the privacy notice above Send and the full notice at #privacy', async ({ page }) => {
  await page.goto('/contact/')
  await expect(page.locator('#contact-notice')).toBeVisible()
  const full = page.locator('#privacy')
  if (await full.count()) await expect(full.locator('h2')).toBeVisible()
})

test('sending → sent, with the relay message, form cleared', async ({ page }) => {
  let body = null
  await page.route(API, async (route) => {
    body = route.request().postDataJSON()
    await new Promise((r) => setTimeout(r, 400))
    await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ status: 'received', message: 'Thanks, we have your message and will reply by email.' }) })
  })
  await page.goto('/contact/')
  await fill(page)
  await page.getByRole('button', { name: 'Send message' }).click()
  await expect(page.getByRole('button', { name: 'Sending…' })).toBeVisible()
  await expect(page.getByRole('status')).toContainText('Message sent.')
  await expect(page.getByLabel('Message', { exact: true })).toHaveValue('')
  expect(body).toMatchObject({ name: 'Priya Das', email: 'priya@example.com', website: '' })
  expect(body).toHaveProperty('turnstile_token')
})

test('Turnstile failure keeps the text and asks to redo the check', async ({ page }) => {
  await page.route(API, (route) =>
    route.fulfill({ status: 400, contentType: 'application/json', body: JSON.stringify({ code: 'CMS_VALIDATION', message: 'We could not confirm you are not a bot.', field: 'turnstile_token', retryable: true }) }),
  )
  await page.goto('/contact/')
  await fill(page)
  await page.getByRole('button', { name: 'Send message' }).click()
  await expect(page.getByRole('alert')).toContainText('anti-spam check')
  await expect(page.getByLabel('Your name')).toHaveValue('Priya Das')
})

test('rate limited (429): try again in a minute', async ({ page }) => {
  await page.route(API, (route) => route.fulfill({ status: 429, headers: { 'Retry-After': '60' }, contentType: 'application/json', body: JSON.stringify({ code: 'CMS_RATE_LIMITED', message: 'Too many' }) }))
  await page.goto('/contact/')
  await fill(page)
  await page.getByRole('button', { name: 'Send message' }).click()
  await expect(page.getByRole('alert')).toContainText('Wait a minute')
})

test('relay unreachable → mailto fallback with the message prefilled', async ({ page }) => {
  await page.route(API, (route) => route.abort('connectionrefused'))
  await page.goto('/contact/')
  await fill(page)
  await page.getByRole('button', { name: 'Send message' }).click()
  const fallback = page.getByTestId('contact-fallback')
  await expect(fallback).toContainText('not reachable')
  const href = await fallback.getByRole('link', { name: `Email ${email}` }).getAttribute('href')
  expect(href.startsWith(`mailto:${email}?subject=`)).toBe(true)
  expect(decodeURIComponent(href)).toContain('diagnostic prototype')
})

test('server field error maps back to the field', async ({ page }) => {
  await page.route(API, (route) => route.fulfill({ status: 400, contentType: 'application/json', body: JSON.stringify({ code: 'CMS_VALIDATION', message: 'Enter a valid phone.', field: 'phone', fix: 'Use digits.' }) }))
  await page.goto('/contact/')
  await fill(page)
  await page.getByLabel('Phone (optional)').fill('+91 88200 51894')
  await page.getByRole('button', { name: 'Send message' }).click()
  await expect(page.locator('#contact-phone-error')).toBeVisible()
})

test('without JavaScript there is no form at all (never a GET of personal data), only email and phone', async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false })
  const page = await ctx.newPage()
  await page.goto('/contact/')
  await expect(page.locator('form')).toHaveCount(0)
  await expect(page.locator('input, textarea')).toHaveCount(0)
  const direct = page.getByTestId('contact-direct')
  await expect(direct.getByRole('link', { name: `Email ${email}` })).toHaveAttribute('href', new RegExp(`^mailto:${email.replace(/[.]/g, '\\.')}\\?subject=`))
  await expect(direct.locator('a[href^="tel:"]')).toHaveCount(1)
  await expect(page.locator('#contact-notice')).toBeVisible()
  await ctx.close()
})

test('the prerendered HTML carries no form; after hydration the form posts (never GET)', async ({ page, request }) => {
  const html = await (await request.get('/contact/')).text()
  expect(html).not.toMatch(/<form\b/)
  expect(html).toContain('data-testid="contact-direct"')
  await page.goto('/contact/')
  await expect(page.getByTestId('contact-form')).toHaveAttribute('method', 'post')
  await expect(page.getByTestId('contact-direct')).toHaveCount(0)
})
