gcloud services enable \
  aiplatform.googleapis.com \
  analyticshub.googleapis.com \
  appengine.googleapis.com \
  artifactregistry.googleapis.com \
  bigquery.googleapis.com \
  bigqueryconnection.googleapis.com \
  bigquerydatapolicy.googleapis.com \
  bigquerydatatransfer.googleapis.com \
  bigquerymigration.googleapis.com \
  bigqueryreservation.googleapis.com \
  bigquerystorage.googleapis.com \
  cloudaicompanion.googleapis.com \
  cloudasset.googleapis.com \
  cloudbuild.googleapis.com \
  cloudfunctions.googleapis.com \
  cloudresourcemanager.googleapis.com \
  cloudtrace.googleapis.com \
  compute.googleapis.com &

gcloud services enable \
  datastore.googleapis.com \
  developerconnect.googleapis.com \
  discoveryengine.googleapis.com \
  dns.googleapis.com \
  domains.googleapis.com \
  fcm.googleapis.com \
  firebase.googleapis.com \
  firebaseappdistribution.googleapis.com \
  firebaseapphosting.googleapis.com \
  firebasehosting.googleapis.com \
  firebaseinstallations.googleapis.com \
  firebaseremoteconfig.googleapis.com \
  firebaserules.googleapis.com &

gcloud services enable \
  geminicloudassist.googleapis.com \
  oslogin.googleapis.com \
  pubsub.googleapis.com \
  recommender.googleapis.com \
  run.googleapis.com \
  runtimeconfig.googleapis.com \
  secretmanager.googleapis.com \
  servicemanagement.googleapis.com \
  serviceusage.googleapis.com \
  storage.googleapis.com \
  testing.googleapis.com \
  workstations.googleapis.com \
  iap.googleapis.com \
  identitytoolkit.googleapis.com &

wait
echo "Finished enabling APIs"

