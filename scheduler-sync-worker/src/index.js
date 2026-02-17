/**
 * Cloudflare Worker for Daily Scheduler data sync
 * Handles upload/download of JSON files to/from R2 bucket
 */

export default {
	async fetch(request, env, ctx) {
		const url = new URL(request.url);
		const path = url.pathname;

		// CORS headers for all responses
		const corsHeaders = {
			'Access-Control-Allow-Origin': '*',
			'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
			'Access-Control-Allow-Headers': 'Content-Type',
		};

		// Handle CORS preflight
		if (request.method === 'OPTIONS') {
			return new Response(null, { headers: corsHeaders });
		}

		try {
			// Route: GET /list - List all files in bucket
			if (path === '/list' && request.method === 'GET') {
				const list = await env.SCHEDULER_DATA.list();
				return new Response(
					JSON.stringify({
						files: list.objects.map(obj => obj.key),
						count: list.objects.length
					}),
					{
						headers: {
							...corsHeaders,
							'Content-Type': 'application/json'
						}
					}
				);
			}

			// Route: POST /upload - Upload a JSON file to R2
			if (path === '/upload' && request.method === 'POST') {
				const body = await request.json();
				const { filename, content } = body;

				if (!filename || !content) {
					return new Response(
						JSON.stringify({ error: 'Missing filename or content' }),
						{
							status: 400,
							headers: { ...corsHeaders, 'Content-Type': 'application/json' }
						}
					);
				}

				// Validate filename (only allow specific JSON files)
				const allowedFiles = [
					'config.json',
					'tasks.json',
					'timer_state.json',
					'completed_log.json',
					'incomplete_history.json',
					'daily_stats.json'
				];

				if (!allowedFiles.includes(filename)) {
					return new Response(
						JSON.stringify({ error: 'Invalid filename. Only scheduler JSON files allowed.' }),
						{
							status: 400,
							headers: { ...corsHeaders, 'Content-Type': 'application/json' }
						}
					);
				}

				// Upload to R2
				await env.SCHEDULER_DATA.put(filename, content, {
					httpMetadata: {
						contentType: 'application/json'
					}
				});

				return new Response(
					JSON.stringify({
						success: true,
						filename: filename,
						size: content.length
					}),
					{
						headers: { ...corsHeaders, 'Content-Type': 'application/json' }
					}
				);
			}

			// Route: GET /download/:filename - Download a JSON file from R2
			if (path.startsWith('/download/') && request.method === 'GET') {
				const filename = path.substring('/download/'.length);

				const object = await env.SCHEDULER_DATA.get(filename);

				if (object === null) {
					return new Response(
						JSON.stringify({ error: 'File not found' }),
						{
							status: 404,
							headers: { ...corsHeaders, 'Content-Type': 'application/json' }
						}
					);
				}

				return new Response(object.body, {
					headers: {
						...corsHeaders,
						'Content-Type': 'application/json'
					}
				});
			}

			// Default: Show API documentation
			if (path === '/' && request.method === 'GET') {
				return new Response(
					JSON.stringify({
						service: 'Daily Scheduler Sync API',
						version: '1.0.0',
						endpoints: {
							'GET /list': 'List all files in bucket',
							'POST /upload': 'Upload JSON file (body: {filename, content})',
							'GET /download/:filename': 'Download JSON file from R2'
						},
						allowed_files: [
							'config.json',
							'tasks.json',
							'timer_state.json',
							'completed_log.json',
							'incomplete_history.json',
							'daily_stats.json'
						]
					}),
					{
						headers: { ...corsHeaders, 'Content-Type': 'application/json' }
					}
				);
			}

			// Not found
			return new Response(
				JSON.stringify({ error: 'Not found' }),
				{
					status: 404,
					headers: { ...corsHeaders, 'Content-Type': 'application/json' }
				}
			);

		} catch (error) {
			return new Response(
				JSON.stringify({ error: error.message }),
				{
					status: 500,
					headers: { ...corsHeaders, 'Content-Type': 'application/json' }
				}
			);
		}
	},
};
