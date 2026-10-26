const { beforeUserSignedIn } = require("firebase-functions/v2/identity");
const { initializeApp } = require("firebase-admin/app");
const { getAuth } = require("firebase-admin/auth");
const { SecretManagerServiceClient } = require("@google-cloud/secret-manager");

// Initialize Admin SDK and Secret Manager
initializeApp();
const smClient = new SecretManagerServiceClient();

exports.beforeSignIn = beforeUserSignedIn(async (event) => {
  const user = event.data;
  const credential = event.credential;

  // Intercept and Store Microsoft Tokens
  if (credential && credential.providerId === 'microsoft.com' && credential.accessToken) {
    const tokens = {
      accessToken: credential.accessToken,
      refreshToken: credential.refreshToken || null,
      updatedAt: new Date().toISOString()
    };

    // Grab the explicitly injected environment variable
    const projectId = process.env.PROJECT_ID;
    if (!projectId) {
      console.error("CRITICAL ERROR: PROJECT_ID environment variable is missing.");
      return {};
    }

    // Construct the strict paths required by Secret Manager using client helpers
    const safeUid = user.uid.replace(/[^a-zA-Z0-9_-]/g, '_');
    const secretId = `ms-tokens-${safeUid}`;
    const projectPath = smClient.projectPath(projectId);
    const secretPath = smClient.secretPath(projectId, secretId);

    console.log(`Vaulting tokens for user ${safeUid} at ${secretPath}`);

    try {
      // Step A: Attempt to create the secret container 
      // We do this first; if it exists, we catch the ALREADY_EXISTS error and proceed.
      try {
        await smClient.createSecret({
          parent: projectPath,
          secretId: secretId,
          secret: {
            replication: { automatic: {} },
          },
        });
        console.log(`Created new secret container: ${secretId}`);
      } catch (error) {
        if (error.code === 6) { // ALREADY_EXISTS
          console.log(`Secret container already exists: ${secretId}`);
        } else {
          // Re-throw other errors to be caught by the outer catch block
          throw error;
        }
      }

      // Step B: Add the fresh tokens as a new version
      await smClient.addSecretVersion({
        parent: secretPath,
        payload: {
          data: Buffer.from(JSON.stringify(tokens), 'utf8'),
        },
      });
      console.log(`Successfully added new secret version for user: ${safeUid}`);

    } catch (error) {
      console.error(`Failed to vault Microsoft tokens for user ${safeUid}:`, error);
    }
  }

  return {};
});

