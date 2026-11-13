# Blog Photos

Drop new photos for the website's **Blog** page (husbandoutworld.com/blog/) straight into this folder and push. They join the photo grid under the final blog post.

- **Formats:** `.jpg`, `.jpeg`, `.png` or `.webp`. iPhone `.heic` photos: export them as JPG first.
- **Full size is fine.** The website makes small, fast copies.
- **Order:** the grid runs oldest to newest, by the day each photo was taken.
- **Dates:** read from the photo's own camera data. If a photo has none, a date in its file name works too (`PXL_20240628_...`, `IMG-20240628-...`, `2024-06-28 con.jpg`). On the website each photo is named after its date (`2024-06-28.webp`).
- **Descriptions, or a date the photo doesn't carry:** add the photo to [content/blog-photos.json](../../../content/blog-photos.json):
  ```json
  { "file": "Blog Photos/PXL_20240628_161337.jpg", "date": "2024-06-28", "description": "Our booth at the convention" }
  ```
  The description shows under the photo when it's opened, and screen readers read it.
- **Location privacy:** phone photos usually carry the GPS spot where they were taken. The website's copies drop it, but the files in this folder keep it, and this repo is public. If you'd rather not publish locations, remove them when you export (Google Photos: Settings › Sharing › "Remove geo location"; iPhone: Share › Options › turn off Location).

This file isn't a photo, so it never shows on the website.
