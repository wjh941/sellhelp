# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary users are owners and warehouse clerks at a food and grocery wholesale stall. Many users operate on Windows desktop computers at 100-125% display scaling and need clear, comfortably sized controls for repeated daily work.

## Product Purpose

Yingtai Food Trading Management System supports daily purchase receiving, sales order entry, inventory control, customer receivables, returns, market records, pricing references, weekly reporting, and business-advisor questions for a food wholesale operation.

## Positioning

The product keeps operational data in a local FastAPI and SQLite application while giving staff one workflow-oriented interface for stock, orders, receivables, and management decisions.

## Operating Context

The product is used during receiving, counter sales, delivery preparation, stock checks, customer repayment follow-up, and weekly review. Sales order entry and purchase receiving are high-frequency workflows. Operators need to see stock, price levels, payment status, and risk warnings without losing their current task.

## Capabilities and Constraints

- The frontend is Vue 3, Vite, and Element Plus.
- Existing backend API contracts, SQLite schema, business logic, fields, routes, and `.env` configuration must remain unchanged.
- Client-only interaction state may use localStorage for drafts, table layouts, and chat history. It must not write new data to the backend outside existing API operations.
- Purchase receiving, sales order entry, weekly reports, and business-advisor API behavior must remain unchanged.
- No secret API key may be stored in the browser. Frontend settings may only display server configuration status and instructions available through existing APIs.

## Brand Commitments

- Product name: 盈泰副食贸易部 · 经营管理系统.
- Business-operating interface, not a consumer or cartoon product.
- Light theme is primary with a user-controlled dark theme.
- Brand colors: #165DFF primary, #FF7D00 warning and focus, #F53F3F danger, #00B42A success, and #F2F3F5 neutral background.
- Cards use white surfaces, 8px radius, and restrained shadows.

## Evidence on Hand

- Vue routes and views are in `frontend/src/router/index.js` and `frontend/src/views/`.
- Existing API client and contracts are in `frontend/src/api/index.js`.
- Existing global styles are in `frontend/src/styles/main.scss`.
- No approved imagery or logo asset is present in the project.

## Product Principles

1. Keep high-frequency order entry fast and visually unambiguous.
2. Show risks with color and explicit status labels, never color alone.
3. Preserve the current backend as the source of truth.
4. Make local-only conveniences reversible and visible to the operator.
5. Prefer stable, readable desktop layouts over decorative motion.

## Accessibility & Inclusion

- Tables and forms use at least 14px text; buttons use at least 15px text.
- Controls need generous click targets and clear labels for middle-aged desktop users.
- Light and dark themes must maintain readable contrast and visible keyboard focus.
- Motion is limited to short state and hover feedback, with reduced-motion support.
