# 12.0.2

Tag: v12.0.2
URL: https://github.com/grafana/grafana/releases/tag/v12.0.2

[Download page](https://grafana.com/grafana/download/12.0.2)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Dependencies:** Bump Go to v1.24.4 [#106565](https://github.com/grafana/grafana/pull/106565), [@macabu](https://github.com/macabu)
- **Dependencies:** Bump github.com/openfga/openfga to v1.8.13 to address CVE-2025-48371 [#106116](https://github.com/grafana/grafana/pull/106116), [@macabu](https://github.com/macabu)
- **Storage:** Take `migration_locking` setting into account [#105951](https://github.com/grafana/grafana/pull/105951), [@JohnnyQQQQ](https://github.com/JohnnyQQQQ)

### Bug fixes

- **Alerting:** Fix $value type when single data source is queried [#106101](https://github.com/grafana/grafana/pull/106101), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Fix group-level labels and query_offset in the import API [#106392](https://github.com/grafana/grafana/pull/106392), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Azure:** Fix Application Insights metadata requests [#105838](https://github.com/grafana/grafana/pull/105838), [@aangelisc](https://github.com/aangelisc)
- **Org:** Fix org deletion [#106461](https://github.com/grafana/grafana/pull/106461), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **Security:** Fixes CVE-2025-3415


================================================================================

# 12.0.3

Tag: v12.0.3
URL: https://github.com/grafana/grafana/releases/tag/v12.0.3

[Download page](https://grafana.com/grafana/download/12.0.3)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Bug fixes

- **Security:** Fixes for CVE-2025-6197 and CVE-2025-6023 [#108280](https://github.com/grafana/grafana/pull/108280), [@volcanonoodle](https://github.com/volcanonoodle)


================================================================================

# 12.0.4

Tag: v12.0.4
URL: https://github.com/grafana/grafana/releases/tag/v12.0.4

[Download page](https://grafana.com/grafana/download/12.0.4)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Go:** Update to 1.24.6 [#109317](https://github.com/grafana/grafana/pull/109317), [@Proximyst](https://github.com/Proximyst)

### Bug fixes

- **Azure:** Fix time management field [#108481](https://github.com/grafana/grafana/pull/108481), [@aangelisc](https://github.com/aangelisc)
- **Azure:** Fix time management field [#108481](https://github.com/grafana/grafana/pull/108481), [@aangelisc](https://github.com/aangelisc)
- **Azure:** Fix time management field [#108481](https://github.com/grafana/grafana/pull/108481), [@aangelisc](https://github.com/aangelisc)
- **Azure:** Fix time management field [#108481](https://github.com/grafana/grafana/pull/108481), [@aangelisc](https://github.com/aangelisc)


================================================================================

# 12.0.5

Tag: v12.0.5
URL: https://github.com/grafana/grafana/releases/tag/v12.0.5

[Download page](https://grafana.com/grafana/download/12.0.5)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Alerting:** Update alerting module [#110000](https://github.com/grafana/grafana/pull/110000), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Auditing:** Add settings to control recording of datasource query request and response body (Enterprise)
- **Auditing:** Document new options for recording datasource query request/response body [#109980](https://github.com/grafana/grafana/pull/109980), [@macabu](https://github.com/macabu)

### Bug fixes

- **Alerting:** Fix copying of recording rule fields [#110346](https://github.com/grafana/grafana/pull/110346), [@moustafab](https://github.com/moustafab)
- **Azure:** Fix time management field [#108481](https://github.com/grafana/grafana/pull/108481), [@aangelisc](https://github.com/aangelisc)
- **Fix:** Fix redirection after login when Grafana is served from subpath [#111156](https://github.com/grafana/grafana/pull/111156), [@mgyongyosi](https://github.com/mgyongyosi)

### Plugin development fixes & changes

- **Fix:** Prevent Rollup from treeshaking NPM packages [#110523](https://github.com/grafana/grafana/pull/110523), [@jackw](https://github.com/jackw)


================================================================================

# 12.0.6

Tag: v12.0.6
URL: https://github.com/grafana/grafana/releases/tag/v12.0.6

[Download page](https://grafana.com/grafana/download/12.0.6)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Go:** Update to 1.25.2 + golangci-lint v2.5.0 + golang.org/x/net v0.45.0 [#112161](https://github.com/grafana/grafana/pull/112161), [@macabu](https://github.com/macabu)
- **Go:** Update to 1.25.3 [#112364](https://github.com/grafana/grafana/pull/112364), [@macabu](https://github.com/macabu)

### Bug fixes

- **Auth:** Fix render user OAuth passthrough [#112096](https://github.com/grafana/grafana/pull/112096), [@mgyongyosi](https://github.com/mgyongyosi)
- **FlameGraph:** Ensure total is only counted once for recursive function calls [#111604](https://github.com/grafana/grafana/pull/111604), [@simonswine](https://github.com/simonswine)
- **LDAP Authentication:** Fix URL to propagate username context as parameter [#111847](https://github.com/grafana/grafana/pull/111847), [@bradleypettit](https://github.com/bradleypettit)
- **Plugins:** Dependencies do not inherit parent URL for preinstall [#111766](https://github.com/grafana/grafana/pull/111766), [@wbrowne](https://github.com/wbrowne)


================================================================================

# 12.0.7

Tag: v12.0.7
URL: https://github.com/grafana/grafana/releases/tag/v12.0.7

[Download page](https://grafana.com/grafana/download/12.0.7)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Bug fixes

- **Alerting:** Fix unmarshalling of GettableStatus to include time intervals [#112732](https://github.com/grafana/grafana/pull/112732), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **AnalyticsSummaries:** Fix dashboard rollup not resetting "last X days" metrics to zero (Enterprise)
- **AnalyticsSummaries:** Fix dashboard rollup totals resetting incorrectly (Enterprise)
- **Security:** fix for CVE-2025-41115 in SCIM (System for Cross-domain Identity Management) (Enterprise)


================================================================================

# 12.0.8

Tag: v12.0.8
URL: https://github.com/grafana/grafana/releases/tag/v12.0.8

[Download page](https://grafana.com/grafana/download/12.0.8)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Alerting:** Update alerting dependency [#114252](https://github.com/grafana/grafana/pull/114252), [@moustafab](https://github.com/moustafab)
- **Dependencies:** Bump Go to v1.25.5 [#114756](https://github.com/grafana/grafana/pull/114756), [@macabu](https://github.com/macabu)
- **Docs:** Clarify section title for repeating rows and tabs [#115343](https://github.com/grafana/grafana/pull/115343), [@imatwawana](https://github.com/imatwawana)
- **Plugins:** Add PluginContext to plugins when scenes is disabled [#115061](https://github.com/grafana/grafana/pull/115061), [@hugohaggmark](https://github.com/hugohaggmark)

### Bug fixes

- **Alerting:** Fix contact points issue [#115410](https://github.com/grafana/grafana/pull/115410), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Azure:** Fix `dcount` aggregation [#114904](https://github.com/grafana/grafana/pull/114904), [@aangelisc](https://github.com/aangelisc)
- **Azure:** Fix `percentile` syntax [#114704](https://github.com/grafana/grafana/pull/114704), [@aangelisc](https://github.com/aangelisc)
- **Postgresql:** Fix variable interpolation logic when the variable has multiple values [#114873](https://github.com/grafana/grafana/pull/114873), [@itsmylife](https://github.com/itsmylife)


================================================================================

# 12.0.9

Tag: v12.0.9
URL: https://github.com/grafana/grafana/releases/tag/v12.0.9

[Download page](https://grafana.com/grafana/download/12.0.9)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **API:** Add missing scope check on dashboards [#116892](https://github.com/grafana/grafana/pull/116892), [@Proximyst](https://github.com/Proximyst)
- **Avatar:** Require sign-in, remove queue, respect timeout [#116897](https://github.com/grafana/grafana/pull/116897), [@macabu](https://github.com/macabu)
- **Go:** Update to 1.25.6 [#116401](https://github.com/grafana/grafana/pull/116401), [@macabu](https://github.com/macabu)

### Bug fixes

- **Alerting:** Fix a race condition panic in ResetStateByRuleUID [#115692](https://github.com/grafana/grafana/pull/115692), [@alexander-akhmetov](https://github.com/alexander-akhmetov)


================================================================================

# 12.0.10

Tag: v12.0.10
URL: https://github.com/grafana/grafana/releases/tag/v12.0.10

[Download page](https://grafana.com/grafana/download/12.0.10)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Alerting:** Add limits for the size of expanded notification templates [#117712](https://github.com/grafana/grafana/pull/117712), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Security(Public dashboards annotations):** use dashboard timerange if time selection disabled [#117971](https://github.com/grafana/grafana/pull/117971), [@github-actions[bot]](https://github.com/github-actions[bot])


================================================================================

# 12.1.0

Tag: v12.1.0
URL: https://github.com/grafana/grafana/releases/tag/v12.1.0

[Download page](https://grafana.com/grafana/download/12.1.0)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Access:** Disable role none option if advanced access control is not enabled [#107378](https://github.com/grafana/grafana/pull/107378), [@Jguer](https://github.com/Jguer)
- **Alerting:** Add OAuth2 Support for Webhook Receiver [#106302](https://github.com/grafana/grafana/pull/106302), [@JacobsonMT](https://github.com/JacobsonMT)
- **Alerting:** Add ability to import rules to GMA from Prometheus YAML [#105807](https://github.com/grafana/grafana/pull/105807), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Add details to the payload when tracking import to GMA [#106404](https://github.com/grafana/grafana/pull/106404), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Add export folder action to the new list view [#106256](https://github.com/grafana/grafana/pull/106256), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Add filters for health and contact point in Prometheus Rules api [#106580](https://github.com/grafana/grafana/pull/106580), [@moustafab](https://github.com/moustafab)
- **Alerting:** Add loading spinner for loading groups state [#106289](https://github.com/grafana/grafana/pull/106289), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Add need more info for import ui datasource field [#106364](https://github.com/grafana/grafana/pull/106364), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Add provenance to Prometheus API [#106596](https://github.com/grafana/grafana/pull/106596), [@moustafab](https://github.com/moustafab)
- **Alerting:** Add provenance to remote-ruler extension response (Enterprise)
- **Alerting:** Add simplified routing metadata to the details tab [#106403](https://github.com/grafana/grafana/pull/106403), [@gillesdemey](https://github.com/gillesdemey)
- **Alerting:** Add state history backend to write ALERTS metric [#104361](https://github.com/grafana/grafana/pull/104361), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Add support for Redis Sentinel for Alerting HA [#106322](https://github.com/grafana/grafana/pull/106322), [@vstpme](https://github.com/vstpme)
- **Alerting:** Allow disabling recording rules write for a data source in the UI [#106664](https://github.com/grafana/grafana/pull/106664), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Correctly persist FiredAt in SyncRuleStatePersister [#106658](https://github.com/grafana/grafana/pull/106658), [@fayzal-g](https://github.com/fayzal-g)
- **Alerting:** Ensure errors cleared when Alerting after error [#105246](https://github.com/grafana/grafana/pull/105246), [@moustafab](https://github.com/moustafab)
- **Alerting:** Evaluate all imported from Prometheus rules sequentially [#106295](https://github.com/grafana/grafana/pull/106295), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Extensible Settings module [#107831](https://github.com/grafana/grafana/pull/107831), [@konrad147](https://github.com/konrad147)
- **Alerting:** Filter out rules managed by integrations and add an info alert [#106602](https://github.com/grafana/grafana/pull/106602), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Filter out synthetic datasource-managed rules when importing to GMA [#106358](https://github.com/grafana/grafana/pull/106358), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** List V2 - Add labels popup [#107193](https://github.com/grafana/grafana/pull/107193), [@konrad147](https://github.com/konrad147)
- **Alerting:** List V2 - Grouped view filters [#106400](https://github.com/grafana/grafana/pull/106400), [@konrad147](https://github.com/konrad147)
- **Alerting:** List V2 - Use backend filters for GMA rules [#106897](https://github.com/grafana/grafana/pull/106897), [@konrad147](https://github.com/konrad147)
- **Alerting:** Make paginated rules endpoint strongly consistent (Enterprise)
- **Alerting:** Optimize out unnecessary permission check for rule groups (Enterprise)
- **Alerting:** Optimize prometheus api permission checks [#106299](https://github.com/grafana/grafana/pull/106299), [@moustafab](https://github.com/moustafab)
- **Alerting:** Optimize prometheus api permission checks (Enterprise)
- **Alerting:** Persist alert instance FiredAt field [#105927](https://github.com/grafana/grafana/pull/105927), [@fayzal-g](https://github.com/fayzal-g)
- **Alerting:** Remove ruler from alert list view2 [#106778](https://github.com/grafana/grafana/pull/106778), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Resend alerts for states that are missing in the eval results [#105965](https://github.com/grafana/grafana/pull/105965), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Send notifications immediately on Error|NoData -> Normal transitions [#106421](https://github.com/grafana/grafana/pull/106421), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Support PDC in Grafana-managed recording rules [#106677](https://github.com/grafana/grafana/pull/106677), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Use default_datasource_uid as the default target for recording rules in UI [#106415](https://github.com/grafana/grafana/pull/106415), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Annotations:** Use dashboard uids instead of dashboard ids [#106676](https://github.com/grafana/grafana/pull/106676), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **App Platform Provisioning:** Add experimental nanogit mode for Git Sync [#106763](https://github.com/grafana/grafana/pull/106763), [@MissingRoberto](https://github.com/MissingRoberto)
- **Auth:** Add Azure/Entra workload identity support [#104807](https://github.com/grafana/grafana/pull/104807), [@mehighlow](https://github.com/mehighlow)
- **Auth:** Enable improved session handling by default for OAuth and SAML [#107442](https://github.com/grafana/grafana/pull/107442), [@mgyongyosi](https://github.com/mgyongyosi)
- **Auth:** Enable ssoSettingsLDAP by default [#106310](https://github.com/grafana/grafana/pull/106310), [@mgyongyosi](https://github.com/mgyongyosi)
- **Auth:** Remove api key endpoints [#106019](https://github.com/grafana/grafana/pull/106019), [@dmihai](https://github.com/dmihai)
- **Auth:** Remove code for authenticating API keys [#105998](https://github.com/grafana/grafana/pull/105998), [@dmihai](https://github.com/dmihai)
- **Azure:** Support scope selection in Resource Graph queries [#105835](https://github.com/grafana/grafana/pull/105835), [@aangelisc](https://github.com/aangelisc)
- **Betterer:** Only allow singleton Storage use [#105310](https://github.com/grafana/grafana/pull/105310), [@tskarhed](https://github.com/tskarhed)
- **Caching:** Remove memcached reconnect_interval setting (Enterprise)
- **Chore:** Update k8s.io to v0.33.1 [#105307](https://github.com/grafana/grafana/pull/105307), [@ryantxu](https://github.com/ryantxu)
- **Cloud Monitoring:** Add support for service account impersonation [#107022](https://github.com/grafana/grafana/pull/107022), [@zoltanbedi](https://github.com/zoltanbedi)
- **CloudMigrations:** Add Mute Timings as dependency for Notification Policies [#106751](https://github.com/grafana/grafana/pull/106751), [@macabu](https://github.com/macabu)
- **CloudWatch:** Backport aws-sdk-go-v2 update from external plugin [#107136](https://github.com/grafana/grafana/pull/107136), [@njvrzm](https://github.com/njvrzm)
- **CloudWatch:** Improve instance attribute variable query editor [#105206](https://github.com/grafana/grafana/pull/105206), [@iwysiu](https://github.com/iwysiu)
- **Cloudwatch:** Add missing AWS regions [#106304](https://github.com/grafana/grafana/pull/106304), [@chriscerie](https://github.com/chriscerie)
- **Dashboard Provisioning:** Reduce db load [#106114](https://github.com/grafana/grafana/pull/106114), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **Dashboard:** Add Alert icon in library panels [#107723](https://github.com/grafana/grafana/pull/107723), [@axelavargas](https://github.com/axelavargas)
- **Dashboard:** Add server-configurable quick ranges for the time picker [#102254](https://github.com/grafana/grafana/pull/102254), [@chodges15](https://github.com/chodges15)
- **Dashboard:** Formatting Currency - add new custom 'financial' currency format without abbreviations [#106604](https://github.com/grafana/grafana/pull/106604), [@axelavargas](https://github.com/axelavargas)
- **Dashboard:** Library Panels - Add ability to search by folder name [#106997](https://github.com/grafana/grafana/pull/106997), [@axelavargas](https://github.com/axelavargas)
- **Dashboard:** Schema V2 - Auto-transform V2 dashboards in V1Resource export mode [#105997](https://github.com/grafana/grafana/pull/105997), [@axelavargas](https://github.com/axelavargas)
- **Datasources:** Migrate to new sigv4 middleware (Enterprise)
- **Datasources:** Update grafana-aws-sdk for new sigv4 middleware and aws-sdk-go v1 removal [#107522](https://github.com/grafana/grafana/pull/107522), [@njvrzm](https://github.com/njvrzm)
- **DatePicker:** Add cursor not-allowed style and hover background color [#106451](https://github.com/grafana/grafana/pull/106451), [@ywzheng1](https://github.com/ywzheng1)
- **Dependencies:** Bump Go to v1.24.4 [#106533](https://github.com/grafana/grafana/pull/106533), [@macabu](https://github.com/macabu)
- **Dependencies:** Bump github.com/go-viper/mapstructure/v2 from 2.2.1 to 2.3.0 [#107379](https://github.com/grafana/grafana/pull/107379), [@macabu](https://github.com/macabu)
- **Dependencies:** Bump github.com/openfga/openfga to v1.8.13 to address CVE-2025-48371 [#106064](https://github.com/grafana/grafana/pull/106064), [@macabu](https://github.com/macabu)
- **ElasticSearch:** Remove frontend response parsing [#104148](https://github.com/grafana/grafana/pull/104148), [@nojaf](https://github.com/nojaf)
- **Geomap:** Add HiDPI support to CARTO basemap (#81195) [#106211](https://github.com/grafana/grafana/pull/106211), [@cledwynl](https://github.com/cledwynl)
- **Git Sync UI:** Delete Provisioned Dashboard Flow [#106593](https://github.com/grafana/grafana/pull/106593), [@ywzheng1](https://github.com/ywzheng1)
- **Grafana/data:** Extract fuzzy search core [#107110](https://github.com/grafana/grafana/pull/107110), [@Clarity-89](https://github.com/Clarity-89)
- **I18n:** Update eslint rule to catch some untranslated object properties [#105072](https://github.com/grafana/grafana/pull/105072), [@tomratcliffe](https://github.com/tomratcliffe)
- **InfluxDB:** Add an optional time range filter for tag queries in the query panel autocompleteInflux tag filter [#107195](https://github.com/grafana/grafana/pull/107195), [@NikolayTsvetkov](https://github.com/NikolayTsvetkov)
- **LBAC for data sources:** Adds team filtering for lbac rules (Enterprise)
- **Library Panels:** Mark library panel RBAC as GA & enable by default [#106833](https://github.com/grafana/grafana/pull/106833), [@kaydelaney](https://github.com/kaydelaney)
- **Library Panels:** Modify connection api endpoint to be compatible with unified storage [#107088](https://github.com/grafana/grafana/pull/107088), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **Library elements:** Remove ability to set as "library variable" [#106594](https://github.com/grafana/grafana/pull/106594), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **Library panels:** Remove `libraryPanelRBAC` feature flag, and enable rbac by default [#107222](https://github.com/grafana/grafana/pull/107222), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **Loki:** Remove experimental lokiQuerySplittingConfig [#107298](https://github.com/grafana/grafana/pull/107298), [@ivanahuckova](https://github.com/ivanahuckova)
- **Loki:** Remove experimental predefined operations [#107289](https://github.com/grafana/grafana/pull/107289), [@ivanahuckova](https://github.com/ivanahuckova)
- **OAuth:** Add access token as third source for user info extraction [#107636](https://github.com/grafana/grafana/pull/107636), [@Jguer](https://github.com/Jguer)
- **Plugin Extensions:** Expose PluginMeta generic in usePluginContext [#107577](https://github.com/grafana/grafana/pull/107577), [@MattIPv4](https://github.com/MattIPv4)
- **Postgres:** Switch the datasource plugin from lib/pq to pgx [#103961](https://github.com/grafana/grafana/pull/103961), [@zoltanbedi](https://github.com/zoltanbedi)
- **Preferences:** Use dashboard uid for the home dashboard [#106666](https://github.com/grafana/grafana/pull/106666), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **Profiles:** Stop passing response headers for Grafana-Pyroscope and parca datasources [#106577](https://github.com/grafana/grafana/pull/106577), [@simonswine](https://github.com/simonswine)
- **Prometheus:** Deprecation message for Azure auth [#106490](https://github.com/grafana/grafana/pull/106490), [@bossinc](https://github.com/bossinc)
- **Prometheus:** Facilitate tree shaking with exports and bundler mode [#105575](https://github.com/grafana/grafana/pull/105575), [@NWRichmond](https://github.com/NWRichmond)
- **Prometheus:** Migrate remaining selectors to data-testid [#106564](https://github.com/grafana/grafana/pull/106564), [@idastambuk](https://github.com/idastambuk)
- **ProvisionedFolder:** Delete folder drawer [#107089](https://github.com/grafana/grafana/pull/107089), [@ywzheng1](https://github.com/ywzheng1)
- **Provisioning:** Add pure git repository type [#106815](https://github.com/grafana/grafana/pull/106815), [@MissingRoberto](https://github.com/MissingRoberto)
- **Querying:** Pass dashboard and panel title as headers [#107032](https://github.com/grafana/grafana/pull/107032), [@ivanahuckova](https://github.com/ivanahuckova)
- **Remote Alertmanager:** Send SMTP config [#106337](https://github.com/grafana/grafana/pull/106337), [@santihernandezc](https://github.com/santihernandezc)
- **Restore dashboards:** Add filters and search [#106994](https://github.com/grafana/grafana/pull/106994), [@Clarity-89](https://github.com/Clarity-89)
- **SCIM:** Ignore unsupported fields in user PATCH requests (Enterprise)
- **SCIM:** Implement operation for adding an externalId value to a team (Enterprise)
- **SCIM:** Implement the add members operation in group PATCH requests (Enterprise)
- **SCIM:** Implement the remove members operation in group PATCH requests (Enterprise)
- **SCIM:** Update externalId field in group PATCH request (Enterprise)
- **SQL Expressions:** Always convert on type first [#106083](https://github.com/grafana/grafana/pull/106083), [@kylebrandt](https://github.com/kylebrandt)
- **Select:** Set min width for the current selected item when width=auto [#106131](https://github.com/grafana/grafana/pull/106131), [@tskarhed](https://github.com/tskarhed)
- **StateTimeline:** Display false and empty string values [#107059](https://github.com/grafana/grafana/pull/107059), [@jesdavpet](https://github.com/jesdavpet)
- **StateTimeline:** Support `NaN` and `null` value mappings [#105638](https://github.com/grafana/grafana/pull/105638), [@fastfrwrd](https://github.com/fastfrwrd)
- **Storage:** Take `migration_locking` setting into account [#105938](https://github.com/grafana/grafana/pull/105938), [@JohnnyQQQQ](https://github.com/JohnnyQQQQ)
- **TableNG:** Refactor to better take advantage of react-data-grid [#103755](https://github.com/grafana/grafana/pull/103755), [@leeoniya](https://github.com/leeoniya)
- **Tables:** Pills for Table Cells [#107485](https://github.com/grafana/grafana/pull/107485), [@timlevett](https://github.com/timlevett)
- **Teams:** Add support for updating externalId field [#106406](https://github.com/grafana/grafana/pull/106406), [@dmihai](https://github.com/dmihai)
- **Tempo:** Enable native histograms for Tempo service graph [#105989](https://github.com/grafana/grafana/pull/105989), [@bohandley](https://github.com/bohandley)
- **TimeRangePicker:** Highlight range on hover [#106616](https://github.com/grafana/grafana/pull/106616), [@joshhunt](https://github.com/joshhunt)
- **TraceView:** Resource attributes links extension point [#104680](https://github.com/grafana/grafana/pull/104680), [@edvard-falkskar](https://github.com/edvard-falkskar)
- **Transformations:** Add "Auto" mode to Organize Fields [#103055](https://github.com/grafana/grafana/pull/103055), [@gelicia](https://github.com/gelicia)
- **Transformations:** GA the Regression transformation [#106074](https://github.com/grafana/grafana/pull/106074), [@gelicia](https://github.com/gelicia)
- **Unified storage:** Respect GF_DATABASE_URL override [#105331](https://github.com/grafana/grafana/pull/105331), [@pstibrany](https://github.com/pstibrany)
- **VQB:** Add selected columns to GROUP BY dropdown (#106349) [#106391](https://github.com/grafana/grafana/pull/106391), [@Shubham19032004](https://github.com/Shubham19032004)
- **VQB:** Allow custom table names in TableSelector [#106420](https://github.com/grafana/grafana/pull/106420), [@Victorthedev](https://github.com/Victorthedev)
- **XYChart:** Add support for x=time [#106459](https://github.com/grafana/grafana/pull/106459), [@leeoniya](https://github.com/leeoniya)

### Bug fixes

- **Alerting:** Fix $value type when single data source is queried [#106080](https://github.com/grafana/grafana/pull/106080), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Fix ImportToGMARules flaky test [#106495](https://github.com/grafana/grafana/pull/106495), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Fix RefIds not being shown when creating or editing Grafana-managed recording rule [#106840](https://github.com/grafana/grafana/pull/106840), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Fix contact points tab visibility when user can only create [#106735](https://github.com/grafana/grafana/pull/106735), [@JacobsonMT](https://github.com/JacobsonMT)
- **Alerting:** Fix eval time unit in list view [#106488](https://github.com/grafana/grafana/pull/106488), [@ebuildy](https://github.com/ebuildy)
- **Alerting:** Fix group interval override when adding new rules [#107324](https://github.com/grafana/grafana/pull/107324), [@konrad147](https://github.com/konrad147)
- **Alerting:** Fix group-level labels and query_offset in the import API [#106379](https://github.com/grafana/grafana/pull/106379), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Fix notification policy conflicts originating from provenance mismatch [#107343](https://github.com/grafana/grafana/pull/107343), [@moustafab](https://github.com/moustafab)
- **Alerting:** Fix resolved notifications for same-label Error to Normal transitions [#106210](https://github.com/grafana/grafana/pull/106210), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Hide labels section if we only have private labels [#105996](https://github.com/grafana/grafana/pull/105996), [@gillesdemey](https://github.com/gillesdemey)
- **Annotations:** Remove prometheus from legacy runner [#106737](https://github.com/grafana/grafana/pull/106737), [@scottlepp](https://github.com/scottlepp)
- **Azure:** Fix Application Insights metadata requests [#105614](https://github.com/grafana/grafana/pull/105614), [@aangelisc](https://github.com/aangelisc)
- **Azure:** Fix duplicated trace links [#105698](https://github.com/grafana/grafana/pull/105698), [@aangelisc](https://github.com/aangelisc)
- **Azure:** Fix legend formatting [#106504](https://github.com/grafana/grafana/pull/106504), [@aangelisc](https://github.com/aangelisc)
- **Azure:** Fix resource name determination in template variable queries [#105705](https://github.com/grafana/grafana/pull/105705), [@aangelisc](https://github.com/aangelisc)
- **BarChart/StateTimeline:** Use noValue setting for error message when data is empty [#107147](https://github.com/grafana/grafana/pull/107147), [@fastfrwrd](https://github.com/fastfrwrd)
- **CloudWatch:** Fix http client handling + assume role bug [#107893](https://github.com/grafana/grafana/pull/107893), [@njvrzm](https://github.com/njvrzm)
- **CloudWatch:** Fix proxy transport issue [#107807](https://github.com/grafana/grafana/pull/107807), [@njvrzm](https://github.com/njvrzm)
- **Dashboard:** FF `dashboardNewLayouts` Fix library panels non-editable when multiple added [#107052](https://github.com/grafana/grafana/pull/107052), [@axelavargas](https://github.com/axelavargas)
- **Dashboard:** Fix cache validation to prevent stale cache [#105918](https://github.com/grafana/grafana/pull/105918), [@yashschandra](https://github.com/yashschandra)
- **Dashboard:** Fixes issue with dashboard links that include all variables [#106356](https://github.com/grafana/grafana/pull/106356), [@torkelo](https://github.com/torkelo)
- **Dashboards:** Fix history list for dashboard uids that end in `-` [#107073](https://github.com/grafana/grafana/pull/107073), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **Drilldown:** Fix js crash when using http [#105646](https://github.com/grafana/grafana/pull/105646), [@chu121su12](https://github.com/chu121su12)
- **Fix:** Increase login_attempt.ip_address column length for IPv6 support [#107035](https://github.com/grafana/grafana/pull/107035), [@Jguer](https://github.com/Jguer)
- **FlameGraph:** Fix bug for function names that conflict with JavaScript object prototype properties [#106338](https://github.com/grafana/grafana/pull/106338), [@simonswine](https://github.com/simonswine)
- **Folders:** Correctly resolve nested folder breadcrumbs [#106344](https://github.com/grafana/grafana/pull/106344), [@IevaVasiljeva](https://github.com/IevaVasiljeva)
- **GrafanaUI:** Fix Combobox ignoring loading prop [#105584](https://github.com/grafana/grafana/pull/105584), [@ValeraS](https://github.com/ValeraS)
- **Graphite:** Fix annotation queries [#106553](https://github.com/grafana/grafana/pull/106553), [@aangelisc](https://github.com/aangelisc)
- **Graphite:** Fix date mutation [#107414](https://github.com/grafana/grafana/pull/107414), [@aangelisc](https://github.com/aangelisc)
- **Graphite:** Fix nested variable interpolation for repeated rows [#106976](https://github.com/grafana/grafana/pull/106976), [@aangelisc](https://github.com/aangelisc)
- **K8s:** Dashboards /apis: Fix library element connections [#106734](https://github.com/grafana/grafana/pull/106734), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **Loki:** Fix health check message [#107170](https://github.com/grafana/grafana/pull/107170), [@wooffie](https://github.com/wooffie)
- **Loki:** Fix issue where step parameter using a template variable was marked as invalid [#106541](https://github.com/grafana/grafana/pull/106541), [@ivanahuckova](https://github.com/ivanahuckova)
- **Loki:** Fix label browser not sorted after selection of a label [#107394](https://github.com/grafana/grafana/pull/107394), [@paulojmdias](https://github.com/paulojmdias)
- **Org:** Fix org deletion [#106193](https://github.com/grafana/grafana/pull/106193), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **Plugins:** Fix and encode invalid gRPC header values [#107339](https://github.com/grafana/grafana/pull/107339), [@ivanahuckova](https://github.com/ivanahuckova)
- **PostgreSQL:** Fix error on panel when toggling sqlDatasourceDatabaseSelection feature [#106965](https://github.com/grafana/grafana/pull/106965), [@HasithDeAlwis](https://github.com/HasithDeAlwis)
- **Profiles:** Fix for passing the response headers [#106293](https://github.com/grafana/grafana/pull/106293), [@simonswine](https://github.com/simonswine)
- **Reporting:** Stop sending reports with Never schedule on creation (Enterprise)
- **SCIM:** Fix PUT request for deactivating a user (Enterprise)
- **SCIM:** Fix the removal of all members in group PUT requests (Enterprise)
- **SCIM:** Fix user patch operation (Enterprise)
- **Security:** Add fix for CVE-2025-3580 [#105976](https://github.com/grafana/grafana/pull/105976), [@baldm0mma](https://github.com/baldm0mma)
- **Security:** Fixes for CVE-2025-6197 and CVE-2025-6023 [#108333](https://github.com/grafana/grafana/pull/108333), [@mgyongyosi](https://github.com/mgyongyosi)
- **Settings:** Fix reencryption and rollback of encrypted values in setting table (Enterprise)
- **Tempo:** Fix showing dangling edges in NodeGraph [#107245](https://github.com/grafana/grafana/pull/107245), [@ifrost](https://github.com/ifrost)
- **ToolTip:** Fix flexbox bug with tooltip when `maxWidth` is set manually [#107145](https://github.com/grafana/grafana/pull/107145), [@jdmarshall](https://github.com/jdmarshall)
- **URLParams:** Stringify true values as key=true always (fixes issues with variables with true value) [#106440](https://github.com/grafana/grafana/pull/106440), [@torkelo](https://github.com/torkelo)

### Breaking changes

- **Alerting:** Enable recording rules by default [#105603](https://github.com/grafana/grafana/pull/105603), [@alexander-akhmetov](https://github.com/alexander-akhmetov)

### Plugin development fixes & changes

- **Carousel:** Always center image [#106468](https://github.com/grafana/grafana/pull/106468), [@ashharrison90](https://github.com/ashharrison90)
- **Drawer:** Include divider and close button when passing a custom title element [#106896](https://github.com/grafana/grafana/pull/106896), [@ashharrison90](https://github.com/ashharrison90)


================================================================================

# 12.1.1

Tag: v12.1.1
URL: https://github.com/grafana/grafana/releases/tag/v12.1.1

[Download page](https://grafana.com/grafana/download/12.1.1)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Alerting:** Add rule group name validation to the Prometheus conversion API [#108767](https://github.com/grafana/grafana/pull/108767), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **CloudWatch:** Update grafana/aws-sdk-go with STS endpo… [#109357](https://github.com/grafana/grafana/pull/109357), [@iwysiu](https://github.com/iwysiu)
- **Go:** Update to 1.24.6 [#109318](https://github.com/grafana/grafana/pull/109318), [@Proximyst](https://github.com/Proximyst)

### Bug fixes

- **Alerting:** Fix active time intervals when time interval is renamed [#108547](https://github.com/grafana/grafana/pull/108547), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Alerting:** Fix subpath handling in the alerting package [#109505](https://github.com/grafana/grafana/pull/109505), [@konrad147](https://github.com/konrad147)
- **Config:** Fix date_formats options being moved to a different section [#109366](https://github.com/grafana/grafana/pull/109366), [@joshhunt](https://github.com/joshhunt)


================================================================================

# 12.1.2

Tag: v12.1.2
URL: https://github.com/grafana/grafana/releases/tag/v12.1.2

[Download page](https://grafana.com/grafana/download/12.1.2)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Alerting:** Update alerting module [#109999](https://github.com/grafana/grafana/pull/109999), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Auditing:** Add settings to control recording of datasource query request and response body (Enterprise)
- **Auditing:** Document new options for recording datasource query request/response body [#109981](https://github.com/grafana/grafana/pull/109981), [@macabu](https://github.com/macabu)
- **Chore:** Don't show a "Not found" for public-dashboard fetches if the service is disabled via config [#110144](https://github.com/grafana/grafana/pull/110144), [@mmandrus](https://github.com/mmandrus)
- **CloudWatch:** Use default region when query region is unset [#111079](https://github.com/grafana/grafana/pull/111079), [@iwysiu](https://github.com/iwysiu)

### Bug fixes

- **Alerting:** Fix bug where rules with identical mute/active intervals produced conflicting routes [#110973](https://github.com/grafana/grafana/pull/110973), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Fix copying of recording rule fields [#110312](https://github.com/grafana/grafana/pull/110312), [@moustafab](https://github.com/moustafab)
- **Fix:** Fix redirection after login when Grafana is served from subpath [#111097](https://github.com/grafana/grafana/pull/111097), [@mgyongyosi](https://github.com/mgyongyosi)

### Plugin development fixes & changes

- **Fix:** Prevent Rollup from treeshaking NPM packages [#108570](https://github.com/grafana/grafana/pull/108570), [@jackw](https://github.com/jackw)


================================================================================

# 12.1.3

Tag: v12.1.3
URL: https://github.com/grafana/grafana/releases/tag/v12.1.3

[Download page](https://grafana.com/grafana/download/12.1.3)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Go:** Update to 1.25.2 + golangci-lint v2.5.0 + golang.org/x/net v0.45.0 [#112159](https://github.com/grafana/grafana/pull/112159), [@macabu](https://github.com/macabu)
- **Go:** Update to 1.25.3 [#112362](https://github.com/grafana/grafana/pull/112362), [@macabu](https://github.com/macabu)
- **Table:** Avoid thrown error due to internal React issue [#111945](https://github.com/grafana/grafana/pull/111945), [@fastfrwrd](https://github.com/fastfrwrd)

### Bug fixes

- **Auth:** Fix render user OAuth passthrough [#112097](https://github.com/grafana/grafana/pull/112097), [@mgyongyosi](https://github.com/mgyongyosi)
- **FlameGraph:** Ensure total is only counted once for recursive function calls [#111605](https://github.com/grafana/grafana/pull/111605), [@simonswine](https://github.com/simonswine)
- **LDAP Authentication:** Fix URL to propagate username context as parameter [#111848](https://github.com/grafana/grafana/pull/111848), [@bradleypettit](https://github.com/bradleypettit)
- **Plugins:** Dependencies do not inherit parent URL for preinstall [#111767](https://github.com/grafana/grafana/pull/111767), [@wbrowne](https://github.com/wbrowne)


================================================================================

# 12.1.4

Tag: v12.1.4
URL: https://github.com/grafana/grafana/releases/tag/v12.1.4

[Download page](https://grafana.com/grafana/download/12.1.4)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Bug fixes

- **Alerting:** Fix unmarshalling of GettableStatus to include time intervals [#112733](https://github.com/grafana/grafana/pull/112733), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **AnalyticsSummaries:** Fix dashboard rollup not resetting "last X days" metrics to zero (Enterprise)
- **AnalyticsSummaries:** Fix dashboard rollup totals resetting incorrectly (Enterprise)
- **Security:** fix for CVE-2025-41115 in SCIM (System for Cross-domain Identity Management) (Enterprise)


================================================================================

# 12.1.5

Tag: v12.1.5
URL: https://github.com/grafana/grafana/releases/tag/v12.1.5

[Download page](https://grafana.com/grafana/download/12.1.5)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Alerting:** Update alerting dependency [#114254](https://github.com/grafana/grafana/pull/114254), [@moustafab](https://github.com/moustafab)
- **Dependencies:** Bump Go to v1.25.5 [#114755](https://github.com/grafana/grafana/pull/114755), [@macabu](https://github.com/macabu)
- **Docs:** Clarify section title for repeating rows and tabs [#115344](https://github.com/grafana/grafana/pull/115344), [@imatwawana](https://github.com/imatwawana)
- **Plugins:** Add PluginContext to plugins when scenes is disabled [#115062](https://github.com/grafana/grafana/pull/115062), [@hugohaggmark](https://github.com/hugohaggmark)

### Bug fixes

- **Alerting:** Fix contact points issue [#115411](https://github.com/grafana/grafana/pull/115411), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Azure:** Fix `dcount` aggregation [#114905](https://github.com/grafana/grafana/pull/114905), [@aangelisc](https://github.com/aangelisc)
- **Azure:** Fix `percentile` syntax [#114705](https://github.com/grafana/grafana/pull/114705), [@aangelisc](https://github.com/aangelisc)
- **Postgresql:** Fix variable interpolation logic when the variable has multiple values [#114874](https://github.com/grafana/grafana/pull/114874), [@itsmylife](https://github.com/itsmylife)


================================================================================

# 12.1.6

Tag: v12.1.6
URL: https://github.com/grafana/grafana/releases/tag/v12.1.6

[Download page](https://grafana.com/grafana/download/12.1.6)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **API:** Add missing scope check on dashboards [#116890](https://github.com/grafana/grafana/pull/116890), [@Proximyst](https://github.com/Proximyst)
- **Avatar:** Require sign-in, remove queue, respect timeout [#116896](https://github.com/grafana/grafana/pull/116896), [@macabu](https://github.com/macabu)
- **Go:** Update to 1.25.6 [#116400](https://github.com/grafana/grafana/pull/116400), [@macabu](https://github.com/macabu)

### Bug fixes

- **Alerting:** Fix a race condition panic in ResetStateByRuleUID [#115693](https://github.com/grafana/grafana/pull/115693), [@alexander-akhmetov](https://github.com/alexander-akhmetov)


================================================================================

# 12.1.7

Tag: v12.1.7
URL: https://github.com/grafana/grafana/releases/tag/v12.1.7

[Download page](https://grafana.com/grafana/download/12.1.7)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Alerting:** Add limits for the size of expanded notification templates [#117711](https://github.com/grafana/grafana/pull/117711), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Correlations:** Remove support for org_id=0 [#116957](https://github.com/grafana/grafana/pull/116957), [@gelicia](https://github.com/gelicia)
- **Go:** Update to 1.25.7 [#117474](https://github.com/grafana/grafana/pull/117474), [@macabu](https://github.com/macabu)
- **Security(Public dashboards annotations):** use dashboard timerange if time selection disabled [#117863](https://github.com/grafana/grafana/pull/117863), [@github-actions[bot]](https://github.com/github-actions[bot])


================================================================================

# 12.1.8

Tag: v12.1.8
URL: https://github.com/grafana/grafana/releases/tag/v12.1.8

[Download page](https://grafana.com/grafana/download/12.1.8)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Bug fixes

- **Dashboard Export:** Fix datasource variable templating in dashboard export [#118321](https://github.com/grafana/grafana/pull/118321), [@kristinademeshchik](https://github.com/kristinademeshchik)


================================================================================

# 12.1.9

Tag: v12.1.9
URL: https://github.com/grafana/grafana/releases/tag/v12.1.9

[Download page](https://grafana.com/grafana/download/12.1.9)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Go:** Update to 1.25.8 [#119701](https://github.com/grafana/grafana/pull/119701), [@macabu](https://github.com/macabu)
- **Rendering:** Add support for custom CA certs in Image Renderer [#118912](https://github.com/grafana/grafana/pull/118912), [@mrevutskyi](https://github.com/mrevutskyi)


================================================================================

# 12.1.10

Tag: v12.1.10
URL: https://github.com/grafana/grafana/releases/tag/v12.1.10

[Download page](https://grafana.com/grafana/download/12.1.10)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Bug fixes

- **Security**: Fix CVE-2026-27876
- **Security**: Fix CVE-2026-27877
- **Security**: Fix CVE-2026-28375
- **Security**: Fix CVE-2026-27879
- **Security**: Fix CVE-2026-27880
- **Security**: Fix CVE-2026-27876


================================================================================

# 12.2.0

Tag: v12.2.0
URL: https://github.com/grafana/grafana/releases/tag/v12.2.0

[Download page](https://grafana.com/grafana/download/12.2.0)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- ** Alerting:** Add feedback buttons for the new AI helpers (Enterprise)
- **Access:** Remove plugin app access in plugin basic role seeder (Enterprise)
- **Actions:** Infinity authentication [#109493](https://github.com/grafana/grafana/pull/109493), [@adela-almasan](https://github.com/adela-almasan)
- **Alerting:** Add GMA export to the new list page [#109784](https://github.com/grafana/grafana/pull/109784), [@konrad147](https://github.com/konrad147)
- **Alerting:** Add alerting AI buttons for cloud (Enterprise)
- **Alerting:** Add contact point filter to Active Notifications page [#109775](https://github.com/grafana/grafana/pull/109775), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Add enrichment per rule extension component (Enterprise)
- **Alerting:** Add extension point link from alert rule to grafana-metricsdrilldown-app [#108566](https://github.com/grafana/grafana/pull/108566), [@bohandley](https://github.com/bohandley)
- **Alerting:** Add feature toggle and extension point [#110141](https://github.com/grafana/grafana/pull/110141), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Add keepFiringFor and missing_series_evals_to_resolve to file provisioning [#109699](https://github.com/grafana/grafana/pull/109699), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Add observability to enrichment UI (Enterprise)
- **Alerting:** Add tooltips in enrichment list for enrichment type (Enterprise)
- **Alerting:** Alert enrichment list page (Enterprise)
- **Alerting:** Allow filter by rule source in Filter V2 [#110336](https://github.com/grafana/grafana/pull/110336), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Auto refresh contact points in the rule form [#109539](https://github.com/grafana/grafana/pull/109539), [@konrad147](https://github.com/konrad147)
- **Alerting:** Check if TimeInterval is used in ActiveTimings when deleting [#110691](https://github.com/grafana/grafana/pull/110691), [@fayzal-g](https://github.com/fayzal-g)
- **Alerting:** Disable group consistency check for GMA rules [#109599](https://github.com/grafana/grafana/pull/109599), [@konrad147](https://github.com/konrad147)
- **Alerting:** Display Error Message in Alert History View [#110123](https://github.com/grafana/grafana/pull/110123), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Enrichment Config Form (Enterprise)
- **Alerting:** Filter out private labels before writing recording rules [#109295](https://github.com/grafana/grafana/pull/109295), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** List V2 - Add a group link to the rule list item [#108960](https://github.com/grafana/grafana/pull/108960), [@konrad147](https://github.com/konrad147)
- **Alerting:** List V2 - datasource icons for rules [#109033](https://github.com/grafana/grafana/pull/109033), [@konrad147](https://github.com/konrad147)
- **Alerting:** Load labels in drop-downs without blocking the interaction with the form inputs [#110648](https://github.com/grafana/grafana/pull/110648), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Mark Prometheus to Grafana conversion API as stable [#103499](https://github.com/grafana/grafana/pull/103499), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Move alerting file to an alerting folder [#110257](https://github.com/grafana/grafana/pull/110257), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Support JSON responses in the Prometheus conversion API [#109070](https://github.com/grafana/grafana/pull/109070), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Support extra labels in the Prometheus conversion API [#109136](https://github.com/grafana/grafana/pull/109136), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Support retry with backoff in alert rule evaluation [#99710](https://github.com/grafana/grafana/pull/99710), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Triage alert history with Assistant if available (Enterprise)
- **Auditing:** Add settings to control recording of datasource query request and response body (Enterprise)
- **Auth:** Add setting to disable username based brute force login protection [#109152](https://github.com/grafana/grafana/pull/109152), [@TheoBrigitte](https://github.com/TheoBrigitte)
- **Auth:** Support JWT configs `tls_client_ca` and `jwk_set_bearer_token_file` [#109095](https://github.com/grafana/grafana/pull/109095), [@Baarsgaard](https://github.com/Baarsgaard)
- **Azure:** Resource picker improvements (#109458) [#109520](https://github.com/grafana/grafana/pull/109520), [@aangelisc](https://github.com/aangelisc)
- **Azure:** Show resource group in picker [#110442](https://github.com/grafana/grafana/pull/110442), [@aangelisc](https://github.com/aangelisc)
- **Canvas:** Add option to disable tooltips for one-click elements [#109937](https://github.com/grafana/grafana/pull/109937), [@adela-almasan](https://github.com/adela-almasan)
- **Canvas:** Dynamic connection direction [#108423](https://github.com/grafana/grafana/pull/108423), [@adela-almasan](https://github.com/adela-almasan)
- **Chore:** Remove prometheusCodeModeMetricNamesSearch feature toggle [#109024](https://github.com/grafana/grafana/pull/109024), [@itsmylife](https://github.com/itsmylife)
- **Chore:** Removes HideAngularDeprecation configuration [#110665](https://github.com/grafana/grafana/pull/110665), [@hugohaggmark](https://github.com/hugohaggmark)
- **CloudConfig:** Add config from defaults.ini to StackInfo (Enterprise)
- **CloudWatch:** Append query type to the request id [#109068](https://github.com/grafana/grafana/pull/109068), [@idastambuk](https://github.com/idastambuk)
- **CloudWatch:** Use default region when query region is unset [#109089](https://github.com/grafana/grafana/pull/109089), [@iwysiu](https://github.com/iwysiu)
- **CloudWatch:** Use the correct metric name for errors per function panel in the AWS Lambda sample dashboard [#110718](https://github.com/grafana/grafana/pull/110718), [@kevinwcyu](https://github.com/kevinwcyu)
- **CommandPalette:** Use fuzzySearch util from grafana/data [#108884](https://github.com/grafana/grafana/pull/108884), [@Clarity-89](https://github.com/Clarity-89)
- **Dashboard:** Inspect drawer can no longer be opened with url or linked to [#109617](https://github.com/grafana/grafana/pull/109617), [@torkelo](https://github.com/torkelo)
- **Dashboards:** Add support for full screen panel view and embedded (solo panel) route to repeated panels and new layouts (via new SoloPanelContex) [#107375](https://github.com/grafana/grafana/pull/107375), [@torkelo](https://github.com/torkelo)
- **Dashboards:** Conserve timestamp on time range copy-paste across timezones [#109769](https://github.com/grafana/grafana/pull/109769), [@alik-r](https://github.com/alik-r)
- **Dashboards:** Enable kubernetesDashboards by default [#107618](https://github.com/grafana/grafana/pull/107618), [@dprokop](https://github.com/dprokop)
- **Dashboards:** Make it possible to render variables under a drop-down [#109225](https://github.com/grafana/grafana/pull/109225), [@leventebalogh](https://github.com/leventebalogh)
- **Database:** Add primary key to Settings table (Enterprise)
- **Database:** Add primary key to settings table (Enterprise)
- **Dependencies:** Bump Go to v1.24.5 (Enterprise)
- **Docs:** Deprecate `grafana/grafana-oss` docker repo in favor of `grafana/grafana` [#110065](https://github.com/grafana/grafana/pull/110065), [@kminehart](https://github.com/kminehart)
- **Flame Graph:** Analyze with Grafana Assistant [#108684](https://github.com/grafana/grafana/pull/108684), [@ifrost](https://github.com/ifrost)
- **Folders:** Add team folders feature toggle [#109389](https://github.com/grafana/grafana/pull/109389), [@tomratcliffe](https://github.com/tomratcliffe)
- **Folders:** Update folder using app platform APIs [#110449](https://github.com/grafana/grafana/pull/110449), [@tomratcliffe](https://github.com/tomratcliffe)
- **Folders:** Use app platform search endpoint and update tests [#108814](https://github.com/grafana/grafana/pull/108814), [@tomratcliffe](https://github.com/tomratcliffe)
- **Go:** Update to 1.24.6 [#109313](https://github.com/grafana/grafana/pull/109313), [@Proximyst](https://github.com/Proximyst)
- **InfluxDB:** Ad hoc filters support for expressions [#109344](https://github.com/grafana/grafana/pull/109344), [@aangelisc](https://github.com/aangelisc)
- **Metrics:** Add http_response_size_bytes metric [#110428](https://github.com/grafana/grafana/pull/110428), [@joshhunt](https://github.com/joshhunt)
- **Nested folders:** Remove feature flag [#109212](https://github.com/grafana/grafana/pull/109212), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **NestedFolderPicker:** Add rootFolderUID prop [#109991](https://github.com/grafana/grafana/pull/109991), [@ywzheng1](https://github.com/ywzheng1)
- **P2P Filter:** Add adhoc filter option toggle [#110160](https://github.com/grafana/grafana/pull/110160), [@Develer](https://github.com/Develer)
- **PieChart:** Add panel options for ascending/descending sort, and no sorting [#109564](https://github.com/grafana/grafana/pull/109564), [@cglukas](https://github.com/cglukas)
- **Plugin Extensions:** DataSource Configuration Components [#108350](https://github.com/grafana/grafana/pull/108350), [@shelldandy](https://github.com/shelldandy)
- **Plugins:** Add Connections homepage [#108316](https://github.com/grafana/grafana/pull/108316), [@oshirohugo](https://github.com/oshirohugo)
- **Plugins:** Record plugin version in request metrics [#110210](https://github.com/grafana/grafana/pull/110210), [@njvrzm](https://github.com/njvrzm)
- **Preferences:** Move codegen to apps [#109178](https://github.com/grafana/grafana/pull/109178), [@ryantxu](https://github.com/ryantxu)
- **Prometheus data source:** Migration service [#107364](https://github.com/grafana/grafana/pull/107364), [@bossinc](https://github.com/bossinc)
- **Prometheus:** Refactor metrics modal to handle high cardinality metrics [#108437](https://github.com/grafana/grafana/pull/108437), [@itsmylife](https://github.com/itsmylife)
- **Pyroscope:** Process and display sampling annotations [#109707](https://github.com/grafana/grafana/pull/109707), [@aleks-p](https://github.com/aleks-p)
- **Reporting:** Permit valid but weird emails (Enterprise)
- **Reporting:** Show correct recipient count (Enterprise)
- **Revert:** DataSource: Support config CRUD from apiservers (#106996) [#110342](https://github.com/grafana/grafana/pull/110342), [@njvrzm](https://github.com/njvrzm)
- **Revert:** DataSource: Support config CRUD from apiservers (#8860) (Enterprise)
- **SCIM:** Add flag for rejecting non provisioned users from logging in (Enterprise)
- **SCIM:** Allow empty externalId on update operation (Enterprise)
- **SCIM:** Delete user instead of disabling it on SCIM DELETE user request (Enterprise)
- **SQL Expressions:** Switch feature toggle to public preview [#110473](https://github.com/grafana/grafana/pull/110473), [@kylebrandt](https://github.com/kylebrandt)
- **Table:** Frozen columns [#109276](https://github.com/grafana/grafana/pull/109276), [@fastfrwrd](https://github.com/fastfrwrd)
- **Table:** Max row height for variable height rows [#109639](https://github.com/grafana/grafana/pull/109639), [@fastfrwrd](https://github.com/fastfrwrd)
- **Table:** Tooltip from Field [#109428](https://github.com/grafana/grafana/pull/109428), [@fastfrwrd](https://github.com/fastfrwrd)
- **Table:** Update UX for uniform-reducer case in new footer and overflow [#110493](https://github.com/grafana/grafana/pull/110493), [@fastfrwrd](https://github.com/fastfrwrd)
- **TableNG:** Footer enhancements [#102948](https://github.com/grafana/grafana/pull/102948), [@alexjonspencer1](https://github.com/alexjonspencer1)
- **Text:** Add Inter italic font variants to Grafana UI [#110313](https://github.com/grafana/grafana/pull/110313), [@kapowaz](https://github.com/kapowaz)
- **TraceView:** Refine UI visual hierarchy inside details section [#108929](https://github.com/grafana/grafana/pull/108929), [@ifrost](https://github.com/ifrost)
- **Transformations:** Add empty values options to Transpose [#108421](https://github.com/grafana/grafana/pull/108421), [@gelicia](https://github.com/gelicia)
- **Trend/TimeSeries:** Add "Show values" option [#108090](https://github.com/grafana/grafana/pull/108090), [@HasithDeAlwis](https://github.com/HasithDeAlwis)
- **Trend:** Add support for a logarithmic x axis [#101433](https://github.com/grafana/grafana/pull/101433), [@gelicia](https://github.com/gelicia)
- **Variables:** shows warning when user tries to save erroneous variables [#110154](https://github.com/grafana/grafana/pull/110154), [@hugohaggmark](https://github.com/hugohaggmark)
- **VizTooltip:** Replace `ExemplarHoverView` with `VizTooltip` components [#109369](https://github.com/grafana/grafana/pull/109369), [@adela-almasan](https://github.com/adela-almasan)

### Bug fixes

- **Alerting:** Fix bug where rules with identical mute/active intervals produced conflicting routes [#110971](https://github.com/grafana/grafana/pull/110971), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Fix copying of recording rule fields [#110311](https://github.com/grafana/grafana/pull/110311), [@moustafab](https://github.com/moustafab)
- **Alerting:** Fix field names on webhook HMAC/TLS config HCL export [#110722](https://github.com/grafana/grafana/pull/110722), [@JacobsonMT](https://github.com/JacobsonMT)
- **Alerting:** Fix newly created alert rules not immediately showing up in folder view [#109584](https://github.com/grafana/grafana/pull/109584), [@tomratcliffe](https://github.com/tomratcliffe)
- **Alerting:** Fix permission checks for the Import to GMA [#109950](https://github.com/grafana/grafana/pull/109950), [@konrad147](https://github.com/konrad147)
- **Alerting:** Fix permissions for enrichment routes (Enterprise)
- **Alerting:** Fix subpath handling in the alerting package [#109448](https://github.com/grafana/grafana/pull/109448), [@konrad147](https://github.com/konrad147)
- **Alerting:** Fix wrong import (Enterprise)
- **Alerting:** Hide list view loader if we don't have anything yet [#110464](https://github.com/grafana/grafana/pull/110464), [@gillesdemey](https://github.com/gillesdemey)
- **Alerting:** Set dataSourceName to GRAFANA_RULES_SOURCE_NAME when switch… [#109900](https://github.com/grafana/grafana/pull/109900), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Update alerting module to 10915888e4f099586ad37bea5f4a70f45101d2f5 [#109989](https://github.com/grafana/grafana/pull/109989), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Azure:** Fix logs editor rendering [#109491](https://github.com/grafana/grafana/pull/109491), [@aangelisc](https://github.com/aangelisc)
- **Canvas:** Fix element selection being cleared on panel resize [#110010](https://github.com/grafana/grafana/pull/110010), [@adela-almasan](https://github.com/adela-almasan)
- **CloudConfig:** Fix panic in defaults.ini merge (Enterprise)
- **CloudWatch:** Fix handling region for legacy alerts [#109217](https://github.com/grafana/grafana/pull/109217), [@iwysiu](https://github.com/iwysiu)
- **CloudWatch:** Fix logs query requestId to prevent setting undefined-logs as a requestId [#109930](https://github.com/grafana/grafana/pull/109930), [@kevinwcyu](https://github.com/kevinwcyu)
- **CloudWatch:** Update grafana/aws-sdk-go with STS endpoint bugfix [#109120](https://github.com/grafana/grafana/pull/109120), [@idastambuk](https://github.com/idastambuk)
- **Config:** Fix date_formats options being moved to a different section [#109339](https://github.com/grafana/grafana/pull/109339), [@joshhunt](https://github.com/joshhunt)
- **Dashboard List:** Fix how link query part is created when variables are included [#109861](https://github.com/grafana/grafana/pull/109861), [@aocenas](https://github.com/aocenas)
- **Dashboard versions:** Fix list for large dashboards [#109433](https://github.com/grafana/grafana/pull/109433), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **Dashboard:** Fix AngularJS deprecation in grafana-overview dashboard [#106462](https://github.com/grafana/grafana/pull/106462), [@schoen2](https://github.com/schoen2)
- **Dashboard:** Fixes url links to embedded panels in scene based dashboards [#109837](https://github.com/grafana/grafana/pull/109837), [@torkelo](https://github.com/torkelo)
- **Dashboards:** Fix UTF-8 characters not working with excel downloads by replacing download for excel with excel compatibility mode. [#110099](https://github.com/grafana/grafana/pull/110099), [@oscarkilhed](https://github.com/oscarkilhed)
- **Dashboards:** Fix issue where the time range picker would seemingly be hidden behind the side menu if it was set to always open. [#108607](https://github.com/grafana/grafana/pull/108607), [@oscarkilhed](https://github.com/oscarkilhed)
- **Dashboards:** Fix kiosk mode not persisting through refresh [#110284](https://github.com/grafana/grafana/pull/110284), [@oscarkilhed](https://github.com/oscarkilhed)
- **Dashboards:** Fixing saving and viewing snapshots for repeated panels [#109856](https://github.com/grafana/grafana/pull/109856), [@torkelo](https://github.com/torkelo)
- **Explore:** Fix units overflow for trace durations [#108515](https://github.com/grafana/grafana/pull/108515), [@martincostello](https://github.com/martincostello)
- **Fix:** Install plugins when they have no plugin archive info(catalog en… [#109200](https://github.com/grafana/grafana/pull/109200), [@s4kh](https://github.com/s4kh)
- **InfluxDB:** Fix Unable to use self-signed CA for adding influxdb data source [#105586](https://github.com/grafana/grafana/pull/105586), [@geekeryy](https://github.com/geekeryy)
- **Prometheus:** Don't use incremental querying if one of the queries has $\_\_range variable [#108823](https://github.com/grafana/grafana/pull/108823), [@itsmylife](https://github.com/itsmylife)
- **Prometheus:** Fix eager auto completion [#109128](https://github.com/grafana/grafana/pull/109128), [@itsmylife](https://github.com/itsmylife)
- **Prometheus:** QueryEditor fix error when switching from code to builder for undefined aggregation operations [#110179](https://github.com/grafana/grafana/pull/110179), [@jcolladokuri](https://github.com/jcolladokuri)
- **Pyroscope:** Add start and end date to profiletypes call [#110277](https://github.com/grafana/grafana/pull/110277), [@zoltanbedi](https://github.com/zoltanbedi)
- **Pyroscope:** Fix incorrect rate calculation from flamegraph totals [#110470](https://github.com/grafana/grafana/pull/110470), [@marcsanmi](https://github.com/marcsanmi)
- **Service Accounts:** Fix typo on page indicating none are present [#109560](https://github.com/grafana/grafana/pull/109560), [@eamonryan](https://github.com/eamonryan)
- **Tempo:** Fix instant query streaming [#108924](https://github.com/grafana/grafana/pull/108924), [@adrapereira](https://github.com/adrapereira)
- **TimeSeries:** Use exported time shift and fix time comparison tooltip [#109947](https://github.com/grafana/grafana/pull/109947), [@drew08t](https://github.com/drew08t)
- **Transformations:** Account for group by / count when assessing if calculation is needed [#110546](https://github.com/grafana/grafana/pull/110546), [@gelicia](https://github.com/gelicia)
- **Transforms:** GroupToMatrix transform should retain keyRowField config [#109066](https://github.com/grafana/grafana/pull/109066), [@fastfrwrd](https://github.com/fastfrwrd)

### Breaking changes

- **Alerting:** Enable alertingSaveStateCompressed by default [#109390](https://github.com/grafana/grafana/pull/109390), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Dashboards:** Repeating with no clone keys [#109839](https://github.com/grafana/grafana/pull/109839), [@torkelo](https://github.com/torkelo)
- **Provisioning:** Use inline secrets for gitsync [#109908](https://github.com/grafana/grafana/pull/109908), [@ryantxu](https://github.com/ryantxu)
- **Stars:** Remove deprecated internal ID apis [#110499](https://github.com/grafana/grafana/pull/110499), [@ryantxu](https://github.com/ryantxu)

### Plugin development fixes & changes

- **Drawer:** Truncate Drawer title to just one line [#109540](https://github.com/grafana/grafana/pull/109540), [@joshhunt](https://github.com/joshhunt)
- **Modal:** Center modals at smaller screen heights [#109256](https://github.com/grafana/grafana/pull/109256), [@ashharrison90](https://github.com/ashharrison90)
- **MultiCombobox:** Fix async options to being able to be removed [#109473](https://github.com/grafana/grafana/pull/109473), [@joshhunt](https://github.com/joshhunt)
- **MultiCombobox:** Fix select all when only a single option is available [#109910](https://github.com/grafana/grafana/pull/109910), [@aangelisc](https://github.com/aangelisc)


================================================================================

# 12.2.1

Tag: v12.2.1
URL: https://github.com/grafana/grafana/releases/tag/v12.2.1

[Download page](https://grafana.com/grafana/download/12.2.1)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Go:** Update to 1.25.2 + golangci-lint v2.5.0 + golang.org/x/net v0.45.0 [#112156](https://github.com/grafana/grafana/pull/112156), [@macabu](https://github.com/macabu)
- **Go:** Update to 1.25.3 [#112361](https://github.com/grafana/grafana/pull/112361), [@macabu](https://github.com/macabu)

### Bug fixes

- **Auth:** Fix render user OAuth passthrough [#112092](https://github.com/grafana/grafana/pull/112092), [@mgyongyosi](https://github.com/mgyongyosi)
- **Dashboards:** Fix missing Ctrl+O keyboard shortcut for crosshair toggle [#111402](https://github.com/grafana/grafana/pull/111402), [@ivanortegaalba](https://github.com/ivanortegaalba)
- **Fix:** Fix redirection after login when Grafana is served from subpath [#111069](https://github.com/grafana/grafana/pull/111069), [@mgyongyosi](https://github.com/mgyongyosi)
- **FlameGraph:** Ensure total is only counted once for recursive function calls [#111606](https://github.com/grafana/grafana/pull/111606), [@simonswine](https://github.com/simonswine)
- **LDAP Authentication:** Fix URL to propagate username context as parameter [#111849](https://github.com/grafana/grafana/pull/111849), [@bradleypettit](https://github.com/bradleypettit)
- **Plugins:** Dependencies do not inherit parent URL for preinstall [#111769](https://github.com/grafana/grafana/pull/111769), [@wbrowne](https://github.com/wbrowne)
- **Table:** Backport the Safari 26 fixes to 12.2.1 [#111906](https://github.com/grafana/grafana/pull/111906), [@fastfrwrd](https://github.com/fastfrwrd)


================================================================================

# 12.2.2

Tag: v12.2.2
URL: https://github.com/grafana/grafana/releases/tag/v12.2.2

[Download page](https://grafana.com/grafana/download/12.2.2)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Access control:** Reduce memory usage when fetching user's permissions [#113414](https://github.com/grafana/grafana/pull/113414), [@hairyhenderson](https://github.com/hairyhenderson)
- **Table:** Pill and JSON Cells should allow formatting [#113130](https://github.com/grafana/grafana/pull/113130), [@fastfrwrd](https://github.com/fastfrwrd)

### Bug fixes

- **AnalyticsSummaries:** Fix dashboard rollup not resetting "last X days" metrics to zero (Enterprise)
- **AnalyticsSummaries:** Fix dashboard rollup totals resetting incorrectly (Enterprise)
- **Security:** fix for CVE-2025-41115 in SCIM (System for Cross-domain Identity Management) (Enterprise)


================================================================================

# 12.2.3

Tag: v12.2.3
URL: https://github.com/grafana/grafana/releases/tag/v12.2.3

[Download page](https://grafana.com/grafana/download/12.2.3)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Alerting:** Update alerting dependency [#114256](https://github.com/grafana/grafana/pull/114256), [@moustafab](https://github.com/moustafab)
- **Azure:** Improved column handling in logs query builder [#114840](https://github.com/grafana/grafana/pull/114840), [@aangelisc](https://github.com/aangelisc)
- **Azure:** Include aggregate columns in logs builder [#114834](https://github.com/grafana/grafana/pull/114834), [@aangelisc](https://github.com/aangelisc)
- **Dependencies:** Bump Go to v1.25.5 [#114753](https://github.com/grafana/grafana/pull/114753), [@macabu](https://github.com/macabu)
- **Plugins:** Add PluginContext to plugins when scenes is disabled [#115063](https://github.com/grafana/grafana/pull/115063), [@hugohaggmark](https://github.com/hugohaggmark)
- **QueryEditorRows:** Clear hideSeriesFrom override on query edit [#114629](https://github.com/grafana/grafana/pull/114629), [@Sergej-Vlasov](https://github.com/Sergej-Vlasov)

### Bug fixes

- **Alerting:** Fix contact points issue [#115412](https://github.com/grafana/grafana/pull/115412), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Azure:** Fix `dcount` aggregation [#114906](https://github.com/grafana/grafana/pull/114906), [@aangelisc](https://github.com/aangelisc)
- **Azure:** Fix `percentile` syntax [#114706](https://github.com/grafana/grafana/pull/114706), [@aangelisc](https://github.com/aangelisc)
- **Postgresql:** Fix variable interpolation logic when the variable has multiple values [#114875](https://github.com/grafana/grafana/pull/114875), [@itsmylife](https://github.com/itsmylife)


================================================================================

# 12.2.4

Tag: v12.2.4
URL: https://github.com/grafana/grafana/releases/tag/v12.2.4

[Download page](https://grafana.com/grafana/download/12.2.4)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **API:** Add missing scope check on dashboards [#116889](https://github.com/grafana/grafana/pull/116889), [@Proximyst](https://github.com/Proximyst)
- **Avatar:** Require sign-in, remove queue, respect timeout [#116895](https://github.com/grafana/grafana/pull/116895), [@macabu](https://github.com/macabu)
- **Docs:** Clarify section title for repeating rows and tabs [#115345](https://github.com/grafana/grafana/pull/115345), [@imatwawana](https://github.com/imatwawana)
- **ElasticSearch:** Update annotation time-range properties [#115565](https://github.com/grafana/grafana/pull/115565), [@aangelisc](https://github.com/aangelisc)
- **Explore:** Reset legend when a new query is run [#116589](https://github.com/grafana/grafana/pull/116589), [@ifrost](https://github.com/ifrost)
- **Go:** Update to 1.25.6 [#116399](https://github.com/grafana/grafana/pull/116399), [@macabu](https://github.com/macabu)

### Bug fixes

- **Alerting:** Fix a race condition panic in ResetStateByRuleUID [#115694](https://github.com/grafana/grafana/pull/115694), [@alexander-akhmetov](https://github.com/alexander-akhmetov)


================================================================================

# 12.2.5

Tag: v12.2.5
URL: https://github.com/grafana/grafana/releases/tag/v12.2.5

[Download page](https://grafana.com/grafana/download/12.2.5)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Alerting:** Add limits for the size of expanded notification templates [#117710](https://github.com/grafana/grafana/pull/117710), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Correlations:** Remove support for org_id=0 [#116958](https://github.com/grafana/grafana/pull/116958), [@gelicia](https://github.com/gelicia)
- **Go:** Update to 1.25.7 [#117472](https://github.com/grafana/grafana/pull/117472), [@macabu](https://github.com/macabu)
- **Security(Public dashboards annotations):** use dashboard timerange if time selection disabled [#117861](https://github.com/grafana/grafana/pull/117861), [@github-actions[bot]](https://github.com/github-actions[bot])
- **Security(TraceView):** Sanitize html [#117867](https://github.com/grafana/grafana/pull/117867), [@github-actions[bot]](https://github.com/github-actions[bot])


================================================================================

# 12.2.6

Tag: v12.2.6
URL: https://github.com/grafana/grafana/releases/tag/v12.2.6

[Download page](https://grafana.com/grafana/download/12.2.6)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Bug fixes

- **Dashboard Export:** Fix datasource variable templating in dashboard export [#118324](https://github.com/grafana/grafana/pull/118324), [@kristinademeshchik](https://github.com/kristinademeshchik)


================================================================================

# 12.2.7

Tag: v12.2.7
URL: https://github.com/grafana/grafana/releases/tag/v12.2.7

[Download page](https://grafana.com/grafana/download/12.2.7)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Go:** Update to 1.25.8 [#119696](https://github.com/grafana/grafana/pull/119696), [@macabu](https://github.com/macabu)
- **Rendering:** Add support for custom CA certs in Image Renderer [#118911](https://github.com/grafana/grafana/pull/118911), [@mrevutskyi](https://github.com/mrevutskyi)

### Bug fixes

- **Dashboards:** Fix start parameter in list versions API for K8s backend [#119398](https://github.com/grafana/grafana/pull/119398), [@MissingRoberto](https://github.com/MissingRoberto)


================================================================================

# 12.2.8

Tag: v12.2.8
URL: https://github.com/grafana/grafana/releases/tag/v12.2.8

[Download page](https://grafana.com/grafana/download/12.2.8)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Bug fixes

- **Security:** Fixes CVE-2026-27876
- **Security:** Fixes CVE-2026-27877
- **Security:** Fixes CVE-2026-28375
- **Security:** Fixes CVE-2026-27879
- **Security:** Fixes CVE-2026-27880
- **Security:** Fixes CVE-2026-27876


================================================================================

# 12.3.0

Tag: v12.3.0
URL: https://github.com/grafana/grafana/releases/tag/v12.3.0

[Download page](https://grafana.com/grafana/download/12.3.0)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **API Clients:** Add lazy hooks to clients [#113226](https://github.com/grafana/grafana/pull/113226), [@tomratcliffe](https://github.com/tomratcliffe)
- **API clients:** Automatically set PATCH headers [#111879](https://github.com/grafana/grafana/pull/111879), [@Clarity-89](https://github.com/Clarity-89)
- **API clients:** Extract into a package [#111810](https://github.com/grafana/grafana/pull/111810), [@Clarity-89](https://github.com/Clarity-89)
- **API clients:** Extract into a package (Enterprise)
- **API clients:** Update API clients to include all endpoints & add hooks [#113061](https://github.com/grafana/grafana/pull/113061), [@tomratcliffe](https://github.com/tomratcliffe)
- **AccessControl:** Include hidden roles in service account role display [#112924](https://github.com/grafana/grafana/pull/112924), [@Jguer](https://github.com/Jguer)
- **AccessControl:** Increase limit of LBAC for Datasources rules [#111560](https://github.com/grafana/grafana/pull/111560), [@Jguer](https://github.com/Jguer)
- **Accessibility:** Wrap data source info onto 2 lines at small viewports [#113033](https://github.com/grafana/grafana/pull/113033), [@ashharrison90](https://github.com/ashharrison90)
- **Alert Enrichment:** Add mutator to insert rule UID labels to allow for efficient use of labelSelector (Enterprise)
- **Alerting:** Add enrichment components to rule view page (Enterprise)
- **Alerting:** Add enrichment section to rule view page (Enterprise)
- **Alerting:** Add jitter support for periodic alert state storage to reduce database load spikes [#111357](https://github.com/grafana/grafana/pull/111357), [@softho0n](https://github.com/softho0n)
- **Alerting:** Add position-based matching for identical alert rules [#112407](https://github.com/grafana/grafana/pull/112407), [@konrad147](https://github.com/konrad147)
- **Alerting:** Create alertingAlertRuleFormSchema in restrictedGrafanaApis [#112794](https://github.com/grafana/grafana/pull/112794), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Display error message in central state history view [#111445](https://github.com/grafana/grafana/pull/111445), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Enrichment per rule wip-2 (Enterprise)
- **Alerting:** Hide metadata if grouping by folder [#113216](https://github.com/grafana/grafana/pull/113216), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Improve template ai helper prompt and add some examples (Enterprise)
- **Alerting:** Move enrichment tab between details and versions [#110886](https://github.com/grafana/grafana/pull/110886), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Remove ai feedback button from alert form [#112713](https://github.com/grafana/grafana/pull/112713), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Remove unused components [#111320](https://github.com/grafana/grafana/pull/111320), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Remove useRulesSourcesWithRuler for SmartAlertTypeDetector [#111623](https://github.com/grafana/grafana/pull/111623), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Surface remote AM silence creation errors properly [#112757](https://github.com/grafana/grafana/pull/112757), [@moustafab](https://github.com/moustafab)
- **Alerting:** Triage [#110339](https://github.com/grafana/grafana/pull/110339), [@gillesdemey](https://github.com/gillesdemey)
- **Alerting:** Triage rule details drawer [#112055](https://github.com/grafana/grafana/pull/112055), [@konrad147](https://github.com/konrad147)
- **Alerting:** Update prompt examples for template AI Helper (Enterprise)
- **Alerting:** Update width to instance details drawer in Triage page [#113209](https://github.com/grafana/grafana/pull/113209), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Use new enrichment endpoints in FE (Enterprise)
- **Alerting:** Use ruleUid as a prop instead of extracting it from the rule context (Enterprise)
- **Analytics:** Aggregate daily summary in datasources analytics (Enterprise)
- **Analytics:** Apply proper batching to Loki exports and add configurable settings (Enterprise)
- **Annotations:** Exclude internal dashboard id when saved via UID [#111535](https://github.com/grafana/grafana/pull/111535), [@ryantxu](https://github.com/ryantxu)
- **Azure:** Use SSO settings in plugin context [#112058](https://github.com/grafana/grafana/pull/112058), [@aangelisc](https://github.com/aangelisc)
- **Buttons:** Active style for buttons [#111235](https://github.com/grafana/grafana/pull/111235), [@gtk-grafana](https://github.com/gtk-grafana)
- **Caching:** Disable cache if datasource has oauthPassThru=true (Enterprise)
- **Canvas:** Allow non-icon bg image fields [#112308](https://github.com/grafana/grafana/pull/112308), [@fastfrwrd](https://github.com/fastfrwrd)
- **Chore:** Add logsdrilldown replace to apps/iam/go.mod [#112581](https://github.com/grafana/grafana/pull/112581), [@njvrzm](https://github.com/njvrzm)
- **CloudWatch Logs:** Don't add console link to every field in the logs response [#112230](https://github.com/grafana/grafana/pull/112230), [@idastambuk](https://github.com/idastambuk)
- **CloudWatch Logs:** Support Log Anomalies query type [#113067](https://github.com/grafana/grafana/pull/113067), [@idastambuk](https://github.com/idastambuk)
- **CloudWatch:** Add syntax highlighting and autocomplete for logs diff command [#111207](https://github.com/grafana/grafana/pull/111207), [@kevinwcyu](https://github.com/kevinwcyu)
- **CloudWatch:** Add tracking for logs anomalies [#113181](https://github.com/grafana/grafana/pull/113181), [@idastambuk](https://github.com/idastambuk)
- **Dashboard Controls:** Add annotations to the dashboard controls menu [#112816](https://github.com/grafana/grafana/pull/112816), [@leventebalogh](https://github.com/leventebalogh)
- **Dashboard Picker:** Update to use correct search + dashboards APIs [#112341](https://github.com/grafana/grafana/pull/112341), [@tomratcliffe](https://github.com/tomratcliffe)
- **Dashboard:** Backend always set `metricEditorMode: 0` regardless `metricQueryType` and `expression` [#111613](https://github.com/grafana/grafana/pull/111613), [@ivanortegaalba](https://github.com/ivanortegaalba)
- **Dashboards:** Add a new variable type called "Switch" [#111366](https://github.com/grafana/grafana/pull/111366), [@leventebalogh](https://github.com/leventebalogh)
- **Dashboards:** Hide error notifications in kiosk mode on dashboards [#112390](https://github.com/grafana/grafana/pull/112390), [@ivanortegaalba](https://github.com/ivanortegaalba)
- **Dynamic Dashboards:** Expand dashboards_init_dashboard_completed tracking info [#111102](https://github.com/grafana/grafana/pull/111102), [@idastambuk](https://github.com/idastambuk)
- **ErrorBoundary:** Report specific boundary type to Faro [#112071](https://github.com/grafana/grafana/pull/112071), [@tskarhed](https://github.com/tskarhed)
- **Explore:** Use compact mode only when targeting Tempo [#113037](https://github.com/grafana/grafana/pull/113037), [@ifrost](https://github.com/ifrost)
- **FeatureToggles:** Remove deprecated experimental apiserver [#111617](https://github.com/grafana/grafana/pull/111617), [@ryantxu](https://github.com/ryantxu)
- **Fields Selector:** Add component and integrate with Logs and Logs table visualization [#112534](https://github.com/grafana/grafana/pull/112534), [@matyax](https://github.com/matyax)
- **Flame Graph:** Anchor exact match when clicking a table symbol in search [#111101](https://github.com/grafana/grafana/pull/111101), [@samarthbagga-meesho](https://github.com/samarthbagga-meesho)
- **FlameGraph:** Improve prompt for open assistant to analyze flamegraph [#113071](https://github.com/grafana/grafana/pull/113071), [@simonswine](https://github.com/simonswine)
- **FolderPicker:** Don't show expand button for empty folders and move search icon [#111872](https://github.com/grafana/grafana/pull/111872), [@aocenas](https://github.com/aocenas)
- **FolderPicker:** Show parent folder when searching [#111026](https://github.com/grafana/grafana/pull/111026), [@aocenas](https://github.com/aocenas)
- **Geomap:** Add a MapLibre style base layer [#109841](https://github.com/grafana/grafana/pull/109841), [@remogeissbuehler](https://github.com/remogeissbuehler)
- **Geomap:** Move beta layers to GA [#113186](https://github.com/grafana/grafana/pull/113186), [@drew08t](https://github.com/drew08t)
- **Go:** Update to 1.25.2 + golangci-lint v2.5.0 + golang.org/x/net v0.45.0 [#112149](https://github.com/grafana/grafana/pull/112149), [@macabu](https://github.com/macabu)
- **Go:** Update to 1.25.3 [#112359](https://github.com/grafana/grafana/pull/112359), [@macabu](https://github.com/macabu)
- **Grafana Advisor:** Prometheus Type Migration check [#110853](https://github.com/grafana/grafana/pull/110853), [@bossinc](https://github.com/bossinc)
- **Grafana Data Source:** Add random walk configuration options [#113009](https://github.com/grafana/grafana/pull/113009), [@nmarrs](https://github.com/nmarrs)
- **IAM:** Add uid column in team_member DB table [#112439](https://github.com/grafana/grafana/pull/112439), [@dmihai](https://github.com/dmihai)
- **Jaeger:** Migrate API calls to gRPC endpoint [#113297](https://github.com/grafana/grafana/pull/113297), [@jcolladokuri](https://github.com/jcolladokuri)
- **LBAC for data sources:** Provide user feedback of potential performance loss from LBAC rules (Enterprise)
- **Library Panels:** Remove direct use of legacy search [#112231](https://github.com/grafana/grafana/pull/112231), [@tomratcliffe](https://github.com/tomratcliffe)
- **Logs panel:** Respect selected fields for downloading logs [#111753](https://github.com/grafana/grafana/pull/111753), [@matyax](https://github.com/matyax)
- **Nav:** Render menu items as `p` tags so truncation logic can work [#113248](https://github.com/grafana/grafana/pull/113248), [@tomratcliffe](https://github.com/tomratcliffe)
- **Navigation:** Move Cost management and billing plugin to root [#111739](https://github.com/grafana/grafana/pull/111739), [@gubjanos](https://github.com/gubjanos)
- **PanelTimeCompare:** Support saving time compare window [#113150](https://github.com/grafana/grafana/pull/113150), [@torkelo](https://github.com/torkelo)
- **PanelTimeSettings:** Support panel time range settings changes from dashboard in view mode [#113027](https://github.com/grafana/grafana/pull/113027), [@torkelo](https://github.com/torkelo)
- **Plugins:** Install Grafana Pathfinder behind a feature flag [#109909](https://github.com/grafana/grafana/pull/109909), [@Jayclifford345](https://github.com/Jayclifford345)
- **PostgreSQL:** Support PGPASSFILE by making password optional [#108856](https://github.com/grafana/grafana/pull/108856), [@taraspos](https://github.com/taraspos)
- **Provisioning:** Watch file system for changes [#112184](https://github.com/grafana/grafana/pull/112184), [@ryantxu](https://github.com/ryantxu)
- **Reporting:** Add support for schema v2 dashboards (Enterprise)
- **Reporting:** Wait for streaming to end before exporting CSVs (Enterprise)
- **SQL Expressions:** Add Functions to Allow list [#113291](https://github.com/grafana/grafana/pull/113291), [@kylebrandt](https://github.com/kylebrandt)
- **Snapshots:** Use appSubUrl for View all snapshots [#111652](https://github.com/grafana/grafana/pull/111652), [@Clarity-89](https://github.com/Clarity-89)
- **Span Details:** Bring back span id to span details [#112411](https://github.com/grafana/grafana/pull/112411), [@ifrost](https://github.com/ifrost)
- **Span Details:** Wrap label values [#112413](https://github.com/grafana/grafana/pull/112413), [@ifrost](https://github.com/ifrost)
- **Stars:** Refactor StarsToolbarButton and unify nav update logic [#112582](https://github.com/grafana/grafana/pull/112582), [@tomratcliffe](https://github.com/tomratcliffe)
- **Stat/BarGauge:** Border radius tweak [#112562](https://github.com/grafana/grafana/pull/112562), [@torkelo](https://github.com/torkelo)
- **Table:** Add some error-case handling to ImageCell [#110461](https://github.com/grafana/grafana/pull/110461), [@fastfrwrd](https://github.com/fastfrwrd)
- **Table:** Allow FieldType.other containing arrays to use Pills [#111205](https://github.com/grafana/grafana/pull/111205), [@fastfrwrd](https://github.com/fastfrwrd)
- **Table:** Disable virtualization, hover overflow, and scrollbar width resizing on Safari 26 [#111834](https://github.com/grafana/grafana/pull/111834), [@fastfrwrd](https://github.com/fastfrwrd)
- **Table:** Pill and JSON Cells should allow formatting [#111951](https://github.com/grafana/grafana/pull/111951), [@fastfrwrd](https://github.com/fastfrwrd)
- **Table:** Support DataLinks and Actions in SparklineCell [#112244](https://github.com/grafana/grafana/pull/112244), [@fastfrwrd](https://github.com/fastfrwrd)
- **Table:** Update ad-hoc filter to use name instead of displayName [#112815](https://github.com/grafana/grafana/pull/112815), [@fastfrwrd](https://github.com/fastfrwrd)
- **Tempo:** Migrates tags and tag values to datasource backend CallResource requests (Enterprise)
- **Theme:** Changes light theme canvas color a more white shade [#111318](https://github.com/grafana/grafana/pull/111318), [@torkelo](https://github.com/torkelo)
- **Themes:** Update themes border radius [#111478](https://github.com/grafana/grafana/pull/111478), [@torkelo](https://github.com/torkelo)
- **TimeComparison:** Automatically show/hide menu on hover [#112750](https://github.com/grafana/grafana/pull/112750), [@jesdavpet](https://github.com/jesdavpet)
- **TimeSeries:** Allow custom time units on x-axis [#112913](https://github.com/grafana/grafana/pull/112913), [@leeoniya](https://github.com/leeoniya)
- **Timeseries:** Numeric duration values could render as NaN (#73795) [#112076](https://github.com/grafana/grafana/pull/112076), [@fastfrwrd](https://github.com/fastfrwrd)
- **Transformations:** Hide "Match all/any" conditions for less than two filters [#109754](https://github.com/grafana/grafana/pull/109754), [@sudoice](https://github.com/sudoice)
- **UI Extensions:** Remove path validation from link extensions [#112259](https://github.com/grafana/grafana/pull/112259), [@leventebalogh](https://github.com/leventebalogh)

### Bug fixes

- **Access Control:** Fix the permission checks for saving/updating/deleting annotations [#112953](https://github.com/grafana/grafana/pull/112953), [@IevaVasiljeva](https://github.com/IevaVasiljeva)
- **Accessibility:** Improve no-unreduced-motion rule and fix violations [#110304](https://github.com/grafana/grafana/pull/110304), [@tomratcliffe](https://github.com/tomratcliffe)
- **Alerting Provisioning:** Don't error on recording rules without conditions [#109410](https://github.com/grafana/grafana/pull/109410), [@djpnicholls](https://github.com/djpnicholls)
- **Alerting:** Clear outdated settings when switching contact point type [#111869](https://github.com/grafana/grafana/pull/111869), [@konrad147](https://github.com/konrad147)
- **Alerting:** Fix enrichment tab to be rendered only for grafana alerting rules [#113030](https://github.com/grafana/grafana/pull/113030), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Fix instances matching in notification policies [#112326](https://github.com/grafana/grafana/pull/112326), [@konrad147](https://github.com/konrad147)
- **Alerting:** Fix threshold params [#111645](https://github.com/grafana/grafana/pull/111645), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Fix unmarshalling of GettableStatus to include time intervals [#112602](https://github.com/grafana/grafana/pull/112602), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Alerting:** Migrate `spec.title` and `spec.name` fieldSelectors [#111993](https://github.com/grafana/grafana/pull/111993), [@gillesdemey](https://github.com/gillesdemey)
- **Alerting:** Normalize health when filtering rules [#113087](https://github.com/grafana/grafana/pull/113087), [@gillesdemey](https://github.com/gillesdemey)
- **Alerting:** Prohibit receivers with empty name [#113064](https://github.com/grafana/grafana/pull/113064), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Alerting:** Provisioning to fix contact point type on save [#112246](https://github.com/grafana/grafana/pull/112246), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Alerting:** Remove \_\_grafana_origin when duplicating rule [#112396](https://github.com/grafana/grafana/pull/112396), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **AnnoList:** Fix annotations not loading when in a repeated row [#111540](https://github.com/grafana/grafana/pull/111540), [@joshhunt](https://github.com/joshhunt)
- **Annotations:** Fix issue with transformation logic in scenes [#112288](https://github.com/grafana/grafana/pull/112288), [@fastfrwrd](https://github.com/fastfrwrd)
- **Auth:** Fix render user OAuth passthrough [#111636](https://github.com/grafana/grafana/pull/111636), [@charandas](https://github.com/charandas)
- **ComboBox:** Add loading state to dropdown and prefixIcon [#112967](https://github.com/grafana/grafana/pull/112967), [@tomratcliffe](https://github.com/tomratcliffe)
- **Connections:** Fix connections home page on enterprise [#111751](https://github.com/grafana/grafana/pull/111751), [@oshirohugo](https://github.com/oshirohugo)
- **Dashboard:** Fix editor specific permissions in /api [#113292](https://github.com/grafana/grafana/pull/113292), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **Dashboards:** Fix bug with anon users with editor permissions creating dashboards [#113260](https://github.com/grafana/grafana/pull/113260), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **Dashboards:** Fix missing Ctrl+O keyboard shortcut for crosshair toggle [#111310](https://github.com/grafana/grafana/pull/111310), [@ivanortegaalba](https://github.com/ivanortegaalba)
- **Dashboards:** Fix moving to root folder [#111515](https://github.com/grafana/grafana/pull/111515), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **Dashboards:** Fix preload field not being persisted via /v1beta1 [#112475](https://github.com/grafana/grafana/pull/112475), [@ivanortegaalba](https://github.com/ivanortegaalba)
- **Flame Graph:** Use suffix for values formatted with a short formatter [#110999](https://github.com/grafana/grafana/pull/110999), [@ifrost](https://github.com/ifrost)
- **FlameGraph:** Ensure total is only counted once for recursive function calls [#111548](https://github.com/grafana/grafana/pull/111548), [@simonswine](https://github.com/simonswine)
- **FolderPermissions:** Return 404 error when folder does not exist instead of 500 [#112919](https://github.com/grafana/grafana/pull/112919), [@Jguer](https://github.com/Jguer)
- **FolderPicker:** Fix expand toggle also selecting folder [#111755](https://github.com/grafana/grafana/pull/111755), [@aocenas](https://github.com/aocenas)
- **Graphite:** Fix legacy response unmarshalling [#112968](https://github.com/grafana/grafana/pull/112968), [@aangelisc](https://github.com/aangelisc)
- **Histogram:** Properly handle sparse heatmap-cells frames [#112907](https://github.com/grafana/grafana/pull/112907), [@leeoniya](https://github.com/leeoniya)
- **LDAP Authentication:** Fix URL to propagate username context as parameter [#111723](https://github.com/grafana/grafana/pull/111723), [@bradleypettit](https://github.com/bradleypettit)
- **Node graph:** Fix context menu position after scrolling [#112374](https://github.com/grafana/grafana/pull/112374), [@adrapereira](https://github.com/adrapereira)
- **Playlist:** Fix navigation issues with emoji-titled dashboards during dual-write migration [#111659](https://github.com/grafana/grafana/pull/111659), [@axelavargas](https://github.com/axelavargas)
- **Plugin Details Page:** Fix tabs not loading on hard refresh [#112915](https://github.com/grafana/grafana/pull/112915), [@sunker](https://github.com/sunker)
- **Plugin navigation:** Fix active nav item selection when there are more than 10 items in a group [#112886](https://github.com/grafana/grafana/pull/112886), [@aocenas](https://github.com/aocenas)
- **Plugins:** Dependencies do not inherit parent URL for preinstall [#111762](https://github.com/grafana/grafana/pull/111762), [@wbrowne](https://github.com/wbrowne)
- **Plugins:** Set isProvisioned for local plugins without remote counterpart [#111268](https://github.com/grafana/grafana/pull/111268), [@oshirohugo](https://github.com/oshirohugo)
- **Prometheus:** Fix incremental querying logic for public dashboards [#111642](https://github.com/grafana/grafana/pull/111642), [@jcolladokuri](https://github.com/jcolladokuri)
- **Prometheus:** Fix parsing logic of prometheus expressions to honor the order of binary operations [#112220](https://github.com/grafana/grafana/pull/112220), [@jcolladokuri](https://github.com/jcolladokuri)
- **Security:** fix for CVE-2025-41115 in SCIM (System for Cross-domain Identity Management) (Enterprise)
- **SoloPanel:** Fixes issue with solo route and scopes variable [#112769](https://github.com/grafana/grafana/pull/112769), [@torkelo](https://github.com/torkelo)
- **Stars:** Fix starred state not being updated [#111936](https://github.com/grafana/grafana/pull/111936), [@Clarity-89](https://github.com/Clarity-89)
- **Stat:** Fix math for percent change value heights when sparkline is not rendered [#112599](https://github.com/grafana/grafana/pull/112599), [@fastfrwrd](https://github.com/fastfrwrd)
- **StateTimeline:** Fix color display in tooltip [#112878](https://github.com/grafana/grafana/pull/112878), [@fastfrwrd](https://github.com/fastfrwrd)
- **Table:** Fix cell inspect for Sparkline and inferred JSON cells [#113059](https://github.com/grafana/grafana/pull/113059), [@fastfrwrd](https://github.com/fastfrwrd)
- **TextPanel:** Fix `CodeEditor` not appearing properly [#111937](https://github.com/grafana/grafana/pull/111937), [@ashharrison90](https://github.com/ashharrison90)
- **UnitPicker/Cascader:** Fixes type to search for unit feature [#112614](https://github.com/grafana/grafana/pull/112614), [@torkelo](https://github.com/torkelo)
- **VizTooltip:** Better overflow handling on long series names [#112240](https://github.com/grafana/grafana/pull/112240), [@fastfrwrd](https://github.com/fastfrwrd)

### Breaking changes

- **Faro:** Update configuration with best practices [#112108](https://github.com/grafana/grafana/pull/112108), [@joshhunt](https://github.com/joshhunt)
- **LibraryPanels:** Remove unique name constraints [#113077](https://github.com/grafana/grafana/pull/113077), [@ryantxu](https://github.com/ryantxu)
- **RBAC:** Only write action sets [#112429](https://github.com/grafana/grafana/pull/112429), [@IevaVasiljeva](https://github.com/IevaVasiljeva)

### Plugin development fixes & changes

- **Checkbox:** Improve accessibility of the `indeterminate` state [#112388](https://github.com/grafana/grafana/pull/112388), [@ashharrison90](https://github.com/ashharrison90)
- **Collapse:** Improve layout and deprecate `collapsible` prop [#113164](https://github.com/grafana/grafana/pull/113164), [@ashharrison90](https://github.com/ashharrison90)
- **Docs:** Add storybook links to components [#113102](https://github.com/grafana/grafana/pull/113102), [@samsch](https://github.com/samsch)
- **Modal:** Fix button focus being clipped [#112867](https://github.com/grafana/grafana/pull/112867), [@ashharrison90](https://github.com/ashharrison90)
- **Slider:** Expose prop to control visibility of input [#113084](https://github.com/grafana/grafana/pull/113084), [@ashharrison90](https://github.com/ashharrison90)
- **Slider:** Make `inputId` a required param and fix minor a11y violations [#112006](https://github.com/grafana/grafana/pull/112006), [@ashharrison90](https://github.com/ashharrison90)


================================================================================

# 12.3.1

Tag: v12.3.1
URL: https://github.com/grafana/grafana/releases/tag/v12.3.1

[Download page](https://grafana.com/grafana/download/12.3.1)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Alerting:** Update alerting dependency [#114259](https://github.com/grafana/grafana/pull/114259), [@moustafab](https://github.com/moustafab)
- **Azure:** Improved column handling in logs query builder [#114841](https://github.com/grafana/grafana/pull/114841), [@aangelisc](https://github.com/aangelisc)
- **Azure:** Include aggregate columns in logs builder [#114835](https://github.com/grafana/grafana/pull/114835), [@aangelisc](https://github.com/aangelisc)
- **Dependencies:** Bump Go to v1.25.5 [#114751](https://github.com/grafana/grafana/pull/114751), [@macabu](https://github.com/macabu)
- **Docs:** Clarify section title for repeating rows and tabs [#115346](https://github.com/grafana/grafana/pull/115346), [@imatwawana](https://github.com/imatwawana)
- **Plugins:** Add PluginContext to plugins when scenes is disabled [#115064](https://github.com/grafana/grafana/pull/115064), [@hugohaggmark](https://github.com/hugohaggmark)
- **QueryEditorRows:** Clear hideSeriesFrom override on query edit [#114628](https://github.com/grafana/grafana/pull/114628), [@Sergej-Vlasov](https://github.com/Sergej-Vlasov)

### Bug fixes

- **Azure:** Fix `dcount` aggregation [#114907](https://github.com/grafana/grafana/pull/114907), [@aangelisc](https://github.com/aangelisc)
- **Azure:** Fix `percentile` syntax [#114707](https://github.com/grafana/grafana/pull/114707), [@aangelisc](https://github.com/aangelisc)
- **Dashboards:** Fix empty space under time controls when a dashboard has a lot of variables [#114730](https://github.com/grafana/grafana/pull/114730), [@oscarkilhed](https://github.com/oscarkilhed)
- **Plugins:** Datasource breadcrumb link should link to settings tab [#113910](https://github.com/grafana/grafana/pull/113910), [@wbrowne](https://github.com/wbrowne)
- **Postgresql:** Fix variable interpolation logic when the variable has multiple values [#114876](https://github.com/grafana/grafana/pull/114876), [@itsmylife](https://github.com/itsmylife)


================================================================================

# 12.3.2

Tag: v12.3.2
URL: https://github.com/grafana/grafana/releases/tag/v12.3.2

[Download page](https://grafana.com/grafana/download/12.3.2)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **API:** Add missing scope check on dashboards [#116888](https://github.com/grafana/grafana/pull/116888), [@Proximyst](https://github.com/Proximyst)
- **Avatar:** Require sign-in, remove queue, respect timeout [#116893](https://github.com/grafana/grafana/pull/116893), [@macabu](https://github.com/macabu)
- **ElasticSearch:** Update annotation time-range properties [#115566](https://github.com/grafana/grafana/pull/115566), [@aangelisc](https://github.com/aangelisc)
- **Explore:** Reset legend when a new query is run [#116590](https://github.com/grafana/grafana/pull/116590), [@ifrost](https://github.com/ifrost)
- **Go:** Update to 1.25.6 [#116396](https://github.com/grafana/grafana/pull/116396), [@macabu](https://github.com/macabu)

### Bug fixes

- **Alerting:** Fix a race condition panic in ResetStateByRuleUID [#115680](https://github.com/grafana/grafana/pull/115680), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Fix data source recording rules editor [#116303](https://github.com/grafana/grafana/pull/116303), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)


================================================================================

# 12.3.3

Tag: v12.3.3
URL: https://github.com/grafana/grafana/releases/tag/v12.3.3

[Download page](https://grafana.com/grafana/download/12.3.3)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Alerting:** Add limits for the size of expanded notification templates [#117709](https://github.com/grafana/grafana/pull/117709), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Correlations:** Remove support for org_id=0 [#116934](https://github.com/grafana/grafana/pull/116934), [@gelicia](https://github.com/gelicia)
- **Go:** Update to 1.25.7 [#117471](https://github.com/grafana/grafana/pull/117471), [@macabu](https://github.com/macabu)
- **Security(Public dashboards annotations):** use dashboard timerange if time selection disabled [#117860](https://github.com/grafana/grafana/pull/117860), [@dana-axinte](https://github.com/dana-axinte)
- **Security(TraceView):** Sanitize html [#117866](https://github.com/grafana/grafana/pull/117866), [@github-actions[bot]](https://github.com/github-actions[bot])


================================================================================

# 12.3.4

Tag: v12.3.4
URL: https://github.com/grafana/grafana/releases/tag/v12.3.4

[Download page](https://grafana.com/grafana/download/12.3.4)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Bug fixes

- **Dashboard Export:** Fix datasource variable templating in dashboard export [#118327](https://github.com/grafana/grafana/pull/118327), [@kristinademeshchik](https://github.com/kristinademeshchik)
- **Provisioning:** Bump nanogit v0.3.1 with missing objects fixes [#118225](https://github.com/grafana/grafana/pull/118225), [@MissingRoberto](https://github.com/MissingRoberto)


================================================================================

# 12.3.5

Tag: v12.3.5
URL: https://github.com/grafana/grafana/releases/tag/v12.3.5

[Download page](https://grafana.com/grafana/download/12.3.5)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Go:** Update to 1.25.8 [#119694](https://github.com/grafana/grafana/pull/119694), [@macabu](https://github.com/macabu)
- **Rendering:** Add support for custom CA certs in Image Renderer [#118910](https://github.com/grafana/grafana/pull/118910), [@mrevutskyi](https://github.com/mrevutskyi)

### Bug fixes

- **Dashboards:** Fix start parameter in list versions API for K8s backend [#119397](https://github.com/grafana/grafana/pull/119397), [@MissingRoberto](https://github.com/MissingRoberto)


================================================================================

# 12.3.6

Tag: v12.3.6
URL: https://github.com/grafana/grafana/releases/tag/v12.3.6

[Download page](https://grafana.com/grafana/download/12.3.6)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Public Dashboards:** Prevent unintended CRUD operations from different orgs [#120459](https://github.com/grafana/grafana/pull/120459), [@mmandrus](https://github.com/mmandrus)

### Bug fixes

- **Security:** Fixes CVE-2026-27876
- **Security:** Fixes CVE-2026-27877
- **Security:** Fixes CVE-2026-28375
- **Security:** Fixes CVE-2026-27879
- **Security:** Fixes CVE-2026-27880
- **Security:** Fixes CVE-2026-27876


================================================================================

# 12.4.0

Tag: v12.4.0
URL: https://github.com/grafana/grafana/releases/tag/v12.4.0

[Download page](https://grafana.com/grafana/download/12.4.0)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **API:** Add missing scope check on dashboards [#116885](https://github.com/grafana/grafana/pull/116885), [@Proximyst](https://github.com/Proximyst)
- **Alerting Enrichment:** Add new RBAC permissions for reading and writing enrichments (Enterprise)
- **Alerting:** Add Alert Rules tabs navigation with feature toggle [#116253](https://github.com/grafana/grafana/pull/116253), [@aifraenkel](https://github.com/aifraenkel)
- **Alerting:** Add Alert activity card to alerting home page [#115822](https://github.com/grafana/grafana/pull/115822), [@dhalachliyski](https://github.com/dhalachliyski)
- **Alerting:** Add Cursor frontmatter to CLAUDE.md for auto-loading [#115613](https://github.com/grafana/grafana/pull/115613), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Add Edit/Export actions to group rows, clickable folders, and square icon for recording rules [#117763](https://github.com/grafana/grafana/pull/117763), [@konrad147](https://github.com/konrad147)
- **Alerting:** Add RBAC for enrichment [#113296](https://github.com/grafana/grafana/pull/113296), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Add RBAC to enrichments (Enterprise)
- **Alerting:** Add UI for imported time intervals [#116249](https://github.com/grafana/grafana/pull/116249), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Add alert labels as tags on annotations (#28610) [#116244](https://github.com/grafana/grafana/pull/116244), [@msvechla](https://github.com/msvechla)
- **Alerting:** Add alertingSyncNotifiersApiMigration feature flag [#117946](https://github.com/grafana/grafana/pull/117946), [@rodrigopk](https://github.com/rodrigopk)
- **Alerting:** Add compressed periodic save for alert instances [#111803](https://github.com/grafana/grafana/pull/111803), [@softho0n](https://github.com/softho0n)
- **Alerting:** Add counts for firing and pending alert rules [#113309](https://github.com/grafana/grafana/pull/113309), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Add empty state to triage page WIP [#113390](https://github.com/grafana/grafana/pull/113390), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Add expression type information to webhook valueString [#112312](https://github.com/grafana/grafana/pull/112312), [@softho0n](https://github.com/softho0n)
- **Alerting:** Add feature toggle to disable DMA creation in UI [#116830](https://github.com/grafana/grafana/pull/116830), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Add first CLAUDE.md in the frontend alerting folder [#114308](https://github.com/grafana/grafana/pull/114308), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Add folder_uid label to the grafana_alerting_rule_group_rules metric [#115129](https://github.com/grafana/grafana/pull/115129), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Add gh in CLAUDE.md [#114992](https://github.com/grafana/grafana/pull/114992), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Add limits for the size of expanded notification templates [#115242](https://github.com/grafana/grafana/pull/115242), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Alerting:** Add managed folder validation frontend [#115203](https://github.com/grafana/grafana/pull/115203), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Add policy selector in the alert rule form [#117464](https://github.com/grafana/grafana/pull/117464), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Add saved searches feature for alert rules page [#115001](https://github.com/grafana/grafana/pull/115001), [@dhalachliyski](https://github.com/dhalachliyski)
- **Alerting:** Add viz wrapper for run queries in enrichment (Enterprise)
- **Alerting:** Alerts page performance improvements [#113391](https://github.com/grafana/grafana/pull/113391), [@konrad147](https://github.com/konrad147)
- **Alerting:** Analyze an alert rule with Grafana Assistant [#114420](https://github.com/grafana/grafana/pull/114420), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Apply pending period to NoData and Error alerts [#117024](https://github.com/grafana/grafana/pull/117024), [@santihernandezc](https://github.com/santihernandezc)
- **Alerting:** Change group filtering to search-based using lightweight BE endpoint [#114347](https://github.com/grafana/grafana/pull/114347), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Collate alert_rule.namespace_uid column as binary [#115152](https://github.com/grafana/grafana/pull/115152), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Collate rule_group column as binary [#114365](https://github.com/grafana/grafana/pull/114365), [@rwwiv](https://github.com/rwwiv)
- **Alerting:** Config option to set default datasource in Prometheus rule import [#115665](https://github.com/grafana/grafana/pull/115665), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Correct relative paths in CLAUDE.md Required Reading links [#114709](https://github.com/grafana/grafana/pull/114709), [@dhalachliyski](https://github.com/dhalachliyski)
- **Alerting:** Dedicated permission for Template testing API [#115032](https://github.com/grafana/grafana/pull/115032), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Alerting:** Deprecate OpsGenie integration [#117085](https://github.com/grafana/grafana/pull/117085), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Alerting:** Filter out imported contact points from simplified routing dropdown [#116408](https://github.com/grafana/grafana/pull/116408), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Hide DMA options when no manageAlerts datasources exist [#115952](https://github.com/grafana/grafana/pull/115952), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Import to Grafana Alerting Wizard - first iteration [#116924](https://github.com/grafana/grafana/pull/116924), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Improve ASH Loki query efficiency by including folderUID [#113322](https://github.com/grafana/grafana/pull/113322), [@JacobsonMT](https://github.com/JacobsonMT)
- **Alerting:** Improve instance count display [#114997](https://github.com/grafana/grafana/pull/114997), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Make AI Helper in triage to use only assistant (Enterprise)
- **Alerting:** Make default notification configuration use empty receiver [#116368](https://github.com/grafana/grafana/pull/116368), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Alerting:** Make saved search name clickable to apply search [#116832](https://github.com/grafana/grafana/pull/116832), [@dhalachliyski](https://github.com/dhalachliyski)
- **Alerting:** Migrate to K8s style receiver testing API [#116847](https://github.com/grafana/grafana/pull/116847), [@rodrigopk](https://github.com/rodrigopk)
- **Alerting:** Notification configuration tabs [#116749](https://github.com/grafana/grafana/pull/116749), [@aifraenkel](https://github.com/aifraenkel)
- **Alerting:** Prevent routing preview from auto-triggering on mount [#113749](https://github.com/grafana/grafana/pull/113749), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Prevent users from saving rules to git-synced folders [#114944](https://github.com/grafana/grafana/pull/114944), [@rwwiv](https://github.com/rwwiv)
- **Alerting:** Protected fields for Contact points [#115442](https://github.com/grafana/grafana/pull/115442), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Alerting:** Receiver testing via app platform APIs [#111338](https://github.com/grafana/grafana/pull/111338), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Alerting:** Refactor error for duplicate names on notificationPolicy creation [#117797](https://github.com/grafana/grafana/pull/117797), [@rodrigopk](https://github.com/rodrigopk)
- **Alerting:** Replace the static radio button list for notification routing with a dropdown [#117414](https://github.com/grafana/grafana/pull/117414), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Resize created_by and updated_by columns in alert rules tables [#113870](https://github.com/grafana/grafana/pull/113870), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Alerting:** Restrict import UI to admin users only [#117441](https://github.com/grafana/grafana/pull/117441), [@rodrigopk](https://github.com/rodrigopk)
- **Alerting:** Show alert rule scoping in the UI to enrichments list and form (Enterprise)
- **Alerting:** Single alertmanager contact points versions [#116076](https://github.com/grafana/grafana/pull/116076), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Update GOPS labels API calls to v2alpha1 [#116327](https://github.com/grafana/grafana/pull/116327), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Update RuleGroupConfig definitions with missing fields [#115850](https://github.com/grafana/grafana/pull/115850), [@JacobsonMT](https://github.com/JacobsonMT)
- **Alerting:** Update UI of instance counts on triage page [#113660](https://github.com/grafana/grafana/pull/113660), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Update createdBy field when silence is being Recreated [#115543](https://github.com/grafana/grafana/pull/115543), [@paulojmdias](https://github.com/paulojmdias)
- **Alerting:** Update docs for ash AI helper button [#114229](https://github.com/grafana/grafana/pull/114229), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Update import wizard to use policyTreeName as config identifier [#117382](https://github.com/grafana/grafana/pull/117382), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Update logic handling canCreate in integrations version, and handle the new deprecated field in the schema [#116672](https://github.com/grafana/grafana/pull/116672), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Update origin for openAssistant in ash (Enterprise)
- **Alerting:** Update prompt for Analyze rule AI button [#115341](https://github.com/grafana/grafana/pull/115341), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Update prompt for the button 'Analyze rule with assistant' button [#114593](https://github.com/grafana/grafana/pull/114593), [@konrad147](https://github.com/konrad147)
- **Alerting:** Update tooltip message when routing preview is disabled [#113962](https://github.com/grafana/grafana/pull/113962), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Update translations (Enterprise)
- **Alerting:** Use assistant inline hook instead of llm for template ai button (Enterprise)
- **Alerting:** Use canUse instead of provenance to filter out time intervals [#117036](https://github.com/grafana/grafana/pull/117036), [@rodrigopk](https://github.com/rodrigopk)
- **Alerting:** Use data source headers when remote writing [#114528](https://github.com/grafana/grafana/pull/114528), [@santihernandezc](https://github.com/santihernandezc)
- **AppChrome:** Add proper menu icon for menu, logo icon becomes home [#114713](https://github.com/grafana/grafana/pull/114713), [@torkelo](https://github.com/torkelo)
- **Auditing:** Allow configuring Loki retries and timeout (Enterprise)
- **Auditing:** Track uid endpoints for dashboards, not id (Enterprise)
- **Auth:** Add SSO settings PATCH endpoint [#117346](https://github.com/grafana/grafana/pull/117346), [@colin-stuart](https://github.com/colin-stuart)
- **Auth:** Add support for validating OAuth ID token signatures [#116442](https://github.com/grafana/grafana/pull/116442), [@DanCech](https://github.com/DanCech)
- **Auth:** Promote SCIM to GA [#116963](https://github.com/grafana/grafana/pull/116963), [@linoman](https://github.com/linoman)
- **Authz:** Implement Query operation for Zanzana with folder parent retrieval [#113483](https://github.com/grafana/grafana/pull/113483), [@mihai-turdean](https://github.com/mihai-turdean)
- **Avatar:** Require sign-in, remove queue, respect timeout [#116891](https://github.com/grafana/grafana/pull/116891), [@macabu](https://github.com/macabu)
- **Azure Monitor:** Clear filter options in logs builder when key changes [#116329](https://github.com/grafana/grafana/pull/116329), [@aangelisc](https://github.com/aangelisc)
- **Azure:** Improved column handling in logs query builder [#114667](https://github.com/grafana/grafana/pull/114667), [@aangelisc](https://github.com/aangelisc)
- **Azure:** Include aggregate columns in logs builder [#114684](https://github.com/grafana/grafana/pull/114684), [@aangelisc](https://github.com/aangelisc)
- **CandleStick:** Add timeRangePan [#113888](https://github.com/grafana/grafana/pull/113888), [@drew08t](https://github.com/drew08t)
- **Chore:** API: add query params to the spec [#117217](https://github.com/grafana/grafana/pull/117217), [@yudintsevegor](https://github.com/yudintsevegor)
- **Chore:** Access API: add missing query params (Enterprise)
- **Chore:** Deprecate experimental restore dashboard API [#116256](https://github.com/grafana/grafana/pull/116256), [@ryantxu](https://github.com/ryantxu)
- **Chore:** Deprecate the localeFormatPreference feature toggle [#116621](https://github.com/grafana/grafana/pull/116621), [@joshhunt](https://github.com/joshhunt)
- **Chore:** Improve packaging/docker/run.sh [#114012](https://github.com/grafana/grafana/pull/114012), [@dmotte](https://github.com/dmotte)
- **Chore:** RBAC: Migrate role picker to rtkq [#116571](https://github.com/grafana/grafana/pull/116571), [@yudintsevegor](https://github.com/yudintsevegor)
- **Chore:** Remove Drilldown Investigations [#115471](https://github.com/grafana/grafana/pull/115471), [@joey-grafana](https://github.com/joey-grafana)
- **Chore:** Remove `logRequestsInstrumentedAsUnknown` feature flag [#116417](https://github.com/grafana/grafana/pull/116417), [@undef1nd](https://github.com/undef1nd)
- **Chore:** Remove `pinNavItems` feature toggle [#113855](https://github.com/grafana/grafana/pull/113855), [@tomratcliffe](https://github.com/tomratcliffe)
- **Chore:** Remove `unifiedHistory` feature toggle and associated code [#113857](https://github.com/grafana/grafana/pull/113857), [@tomratcliffe](https://github.com/tomratcliffe)
- **Chore:** Remove deprecated language_provider methods in prometheus package [#114361](https://github.com/grafana/grafana/pull/114361), [@itsmylife](https://github.com/itsmylife)
- **Chore:** Remove experimental feature individualCookiePreferences [#116374](https://github.com/grafana/grafana/pull/116374), [@hairyhenderson](https://github.com/hairyhenderson)
- **Chore:** Remove unused+experimental /dashboards/calculate-diff API support [#114151](https://github.com/grafana/grafana/pull/114151), [@ryantxu](https://github.com/ryantxu)
- **Chore:** Rudderstack upgrade to SDK v3 behind flag [#114126](https://github.com/grafana/grafana/pull/114126), [@samsch](https://github.com/samsch)
- **Chore:** Upgrade Grafana Faro to v2, removing `web_vitals_attribution_enabled` [#117516](https://github.com/grafana/grafana/pull/117516), [@tskarhed](https://github.com/tskarhed)
- **Cleanup:** Remove CSV drag-and-drop snapshot query feature [#113645](https://github.com/grafana/grafana/pull/113645), [@fastfrwrd](https://github.com/fastfrwrd)
- **Cloud Monitoring:** Add support for Google Cloud universe_domain [#115931](https://github.com/grafana/grafana/pull/115931), [@aangelisc](https://github.com/aangelisc)
- **CloudMigrations:** Remove feature toggle and introduce config setting to disable it [#114223](https://github.com/grafana/grafana/pull/114223), [@macabu](https://github.com/macabu)
- **CloudWatch Logs:** Hide internal logs field [#114121](https://github.com/grafana/grafana/pull/114121), [@kevinwcyu](https://github.com/kevinwcyu)
- **CloudWatch Logs:** Limit CloudWatch logs queries to use logGroupIdentifiers only for monitoring accounts [#113137](https://github.com/grafana/grafana/pull/113137), [@kevinwcyu](https://github.com/kevinwcyu)
- **CloudWatch Logs:** Select log groups with the log group selector and $\_\_logGroups macro for OpenSearch Structured Query Language queries [#116222](https://github.com/grafana/grafana/pull/116222), [@kevinwcyu](https://github.com/kevinwcyu)
- **CloudWatch:** Add anomaly command to language support, add documentation for anomaly queries [#113311](https://github.com/grafana/grafana/pull/113311), [@idastambuk](https://github.com/idastambuk)
- **CloudWatch:** Add links to data source docs in the config editor [#113795](https://github.com/grafana/grafana/pull/113795), [@kevinwcyu](https://github.com/kevinwcyu)
- **CloudWatch:** Make match exact toggle false by default [#113314](https://github.com/grafana/grafana/pull/113314), [@idastambuk](https://github.com/idastambuk)
- **Cloudwatch:** Make cloudwatchBatchQueries GA [#117448](https://github.com/grafana/grafana/pull/117448), [@iwysiu](https://github.com/iwysiu)
- **Cloudwatch:** Mark missing default region error downstream [#117551](https://github.com/grafana/grafana/pull/117551), [@iwysiu](https://github.com/iwysiu)
- **Cloudwatch:** Update grafana-aws-sdk to 1.4.2 [#115855](https://github.com/grafana/grafana/pull/115855), [@iwysiu](https://github.com/iwysiu)
- **Config:** Set skip migrations in defaults.ini + override when running frontend service locally [#114007](https://github.com/grafana/grafana/pull/114007), [@ashharrison90](https://github.com/ashharrison90)
- **Correlations:** Remove support for org_id=0 [#116877](https://github.com/grafana/grafana/pull/116877), [@gelicia](https://github.com/gelicia)
- **Dashboard :** Allow applying variable regex to display text [#114426](https://github.com/grafana/grafana/pull/114426), [@kristinademeshchik](https://github.com/kristinademeshchik)
- **Dashboard Controls:** Add UI for displaying under menu [#113517](https://github.com/grafana/grafana/pull/113517), [@leventebalogh](https://github.com/leventebalogh)
- **Dashboard provisioning:** Add support for v2 schema [#113620](https://github.com/grafana/grafana/pull/113620), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **Dashboard:** Do not select element always [#116986](https://github.com/grafana/grafana/pull/116986), [@torkelo](https://github.com/torkelo)
- **Dashboard:** Hide sidebar in kiosk mode [#115387](https://github.com/grafana/grafana/pull/115387), [@torkelo](https://github.com/torkelo)
- **Dashboard:** Hide sidebar on mobile when in view mode [#117369](https://github.com/grafana/grafana/pull/117369), [@torkelo](https://github.com/torkelo)
- **Dashboard:** Hide sidebar when playlist is playing [#115414](https://github.com/grafana/grafana/pull/115414), [@torkelo](https://github.com/torkelo)
- **Dashboard:** New experimental time range zoom shortcuts [#114190](https://github.com/grafana/grafana/pull/114190), [@jesdavpet](https://github.com/jesdavpet)
- **Dashboard:** Round x/y/w/h when importing a dashboard with floats [#117072](https://github.com/grafana/grafana/pull/117072), [@bfmatei](https://github.com/bfmatei)
- **Dashboards:** Avoid using internal id from the frontend [#117398](https://github.com/grafana/grafana/pull/117398), [@ryantxu](https://github.com/ryantxu)
- **Dashboards:** Do not show alert rules button for new dashboads [#115571](https://github.com/grafana/grafana/pull/115571), [@torkelo](https://github.com/torkelo)
- **Dashboards:** Make clear all of variable dropdown accessible by keyboard navigation [#117462](https://github.com/grafana/grafana/pull/117462), [@oscarkilhed](https://github.com/oscarkilhed)
- **Dashboards:** Per panel filtering for timeseries [#114499](https://github.com/grafana/grafana/pull/114499), [@mdvictor](https://github.com/mdvictor)
- **Dashboards:** Prevent memory leak in CUE validation by reusing context only for 100 validations [#114818](https://github.com/grafana/grafana/pull/114818), [@MissingRoberto](https://github.com/MissingRoberto)
- **Dashboards:** Remove deprecated dashboard id endpoints [#117227](https://github.com/grafana/grafana/pull/117227), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **DashboardsAPI:** Deprecate /api/dashboards/home [#115333](https://github.com/grafana/grafana/pull/115333), [@ryantxu](https://github.com/ryantxu)
- **DataSources:** Deprecate api routes with name and internal IDs [#116391](https://github.com/grafana/grafana/pull/116391), [@ryantxu](https://github.com/ryantxu)
- **DataSources:** Update SDKs in support of auth service [#112101](https://github.com/grafana/grafana/pull/112101), [@njvrzm](https://github.com/njvrzm)
- **Datagrid:** Deprecate panel [#116071](https://github.com/grafana/grafana/pull/116071), [@natellium](https://github.com/natellium)
- **Datasources:** Experimental API group names use full plugin IDs [#112961](https://github.com/grafana/grafana/pull/112961), [@dafydd-t](https://github.com/dafydd-t)
- **Datasources:** Support new temp creds AWS datasources in auth service (Enterprise)
- **Dependencies:** Bump Go to v1.25.5 [#114749](https://github.com/grafana/grafana/pull/114749), [@macabu](https://github.com/macabu)
- **Docs:** Add Knowledge Graph trace & profile configuration section [#117155](https://github.com/grafana/grafana/pull/117155), [@github-actions[bot]](https://github.com/github-actions[bot])
- **Docs:** Add a "DO NOT MODIFY" warning to the `public/img/*` source code directory [#115502](https://github.com/grafana/grafana/pull/115502), [@jesdavpet](https://github.com/jesdavpet)
- **Docs:** Clarify section title for repeating rows and tabs [#115170](https://github.com/grafana/grafana/pull/115170), [@imatwawana](https://github.com/imatwawana)
- **Docs:** Cleanup enterprise tag usage [#114694](https://github.com/grafana/grafana/pull/114694), [@Hipska](https://github.com/Hipska)
- **Docs:** Cleanup enterprise tag usage (Enterprise)
- **Dynamic Dashboards:** Add new panel button with drag & drop [#116276](https://github.com/grafana/grafana/pull/116276), [@idastambuk](https://github.com/idastambuk)
- **Dynamic Dashboards:** Disallow adding empty row and tab titles [#113941](https://github.com/grafana/grafana/pull/113941), [@idastambuk](https://github.com/idastambuk)
- **Dynamic Dashboards:** Make outline open by default [#114146](https://github.com/grafana/grafana/pull/114146), [@idastambuk](https://github.com/idastambuk)
- **Dynamic Dashboards:** Show hidden variables greyed out [#115723](https://github.com/grafana/grafana/pull/115723), [@idastambuk](https://github.com/idastambuk)
- **EchoSrv:** Enable auto route tracking for Azure App Insights [#113354](https://github.com/grafana/grafana/pull/113354), [@joshhunt](https://github.com/joshhunt)
- **ElasticSearch:** Update annotation time-range properties [#115500](https://github.com/grafana/grafana/pull/115500), [@aangelisc](https://github.com/aangelisc)
- **Elasticsearch:** Add default query mode config setting [#112540](https://github.com/grafana/grafana/pull/112540), [@cauemarcondes](https://github.com/cauemarcondes)
- **Elasticsearch:** Add support for serverless connections [#114855](https://github.com/grafana/grafana/pull/114855), [@cauemarcondes](https://github.com/cauemarcondes)
- **Elasticsearch:** Clear code editor query when switching query types [#116318](https://github.com/grafana/grafana/pull/116318), [@Milad93R](https://github.com/Milad93R)
- **Elasticsearch:** Handle keyed filters buckets and emit frames [#113478](https://github.com/grafana/grafana/pull/113478), [@adamyeats](https://github.com/adamyeats)
- **Elasticsearch:** Raw query editor for DSL [#114066](https://github.com/grafana/grafana/pull/114066), [@bossinc](https://github.com/bossinc)
- **Explore:** Add keyboard shortcut to run queries (#111675) [#115811](https://github.com/grafana/grafana/pull/115811), [@naimeshpatel5295](https://github.com/naimeshpatel5295)
- **Explore:** Ensure data source is part of query object in internal data links [#112949](https://github.com/grafana/grafana/pull/112949), [@ifrost](https://github.com/ifrost)
- **Explore:** Remove use of AppChrome navbar [#114680](https://github.com/grafana/grafana/pull/114680), [@torkelo](https://github.com/torkelo)
- **Explore:** Reset legend when a new query is run [#116323](https://github.com/grafana/grafana/pull/116323), [@ifrost](https://github.com/ifrost)
- **Explore:** Traces query that will work with either logs drilldown or explore [#115837](https://github.com/grafana/grafana/pull/115837), [@gtk-grafana](https://github.com/gtk-grafana)
- **Explore:** Use new Table component [#111463](https://github.com/grafana/grafana/pull/111463), [@SamarthBagga](https://github.com/SamarthBagga)
- **ExternalPlugins:** Restore backward compatability for util function [#113735](https://github.com/grafana/grafana/pull/113735), [@torkelo](https://github.com/torkelo)
- **Feat:** Datasources Auth Service (Enterprise)
- **Feat:** Experimental sandbox mode for community & PPT plugins (Enterprise)
- **Feat:** Experimental sandbox mode for community plugins [#115936](https://github.com/grafana/grafana/pull/115936), [@njvrzm](https://github.com/njvrzm)
- **Feat:** Remove experimental `permissionsFilterRemoveSubquery` feature [#116405](https://github.com/grafana/grafana/pull/116405), [@papagian](https://github.com/papagian)
- **FeatureToggle:** Create experimental `timeRangePan` flag [#112988](https://github.com/grafana/grafana/pull/112988), [@jesdavpet](https://github.com/jesdavpet)
- **FeatureToggle:** Enable time range pan zoom flags by default as generally available [#116970](https://github.com/grafana/grafana/pull/116970), [@jesdavpet](https://github.com/jesdavpet)
- **FieldColor:** Add accessible color palettes [#114424](https://github.com/grafana/grafana/pull/114424), [@ashharrison90](https://github.com/ashharrison90)
- **Folders:** Deprecate `getFolderByUID` method [#113173](https://github.com/grafana/grafana/pull/113173), [@tomratcliffe](https://github.com/tomratcliffe)
- **Folders:** Improve wording for actions and move/delete [#114090](https://github.com/grafana/grafana/pull/114090), [@tomratcliffe](https://github.com/tomratcliffe)
- **Folders:** Manage folder owner reference [#117426](https://github.com/grafana/grafana/pull/117426), [@tomratcliffe](https://github.com/tomratcliffe)
- **Folders:** Send permissions query param with app platform for folder picker [#114158](https://github.com/grafana/grafana/pull/114158), [@tomratcliffe](https://github.com/tomratcliffe)
- **Folders:** Show owner references on folder details pages [#116843](https://github.com/grafana/grafana/pull/116843), [@tomratcliffe](https://github.com/tomratcliffe)
- **Gauge:** Delete radialbar plugin to avoid migrations [#116722](https://github.com/grafana/grafana/pull/116722), [@fastfrwrd](https://github.com/fastfrwrd)
- **Gauge:** Mark grafana/ui export as deprecated [#116436](https://github.com/grafana/grafana/pull/116436), [@fastfrwrd](https://github.com/fastfrwrd)
- **Geomap:** Min/Max Zoom options for XYZ Tile Layer [#114947](https://github.com/grafana/grafana/pull/114947), [@WoozyMasta](https://github.com/WoozyMasta)
- **Geomap:** Variable support in the XYZ Tile layer [#116654](https://github.com/grafana/grafana/pull/116654), [@WoozyMasta](https://github.com/WoozyMasta)
- **Go:** Update to 1.25.6 [#116394](https://github.com/grafana/grafana/pull/116394), [@macabu](https://github.com/macabu)
- **Go:** Update to 1.25.7 [#117470](https://github.com/grafana/grafana/pull/117470), [@macabu](https://github.com/macabu)
- **Grafana Cli:** Add admin flush-rbac-seed-assignment command [#116716](https://github.com/grafana/grafana/pull/116716), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **Grafana Monitoring:** Enable native HTTP histograms by default, make classic histograms configurable [#116534](https://github.com/grafana/grafana/pull/116534), [@undef1nd](https://github.com/undef1nd)
- **GrafanaBootData:** Deprecate config.apps [#115610](https://github.com/grafana/grafana/pull/115610), [@hugohaggmark](https://github.com/hugohaggmark)
- **GrafanaBootData:** Deprecate config.panels [#116918](https://github.com/grafana/grafana/pull/116918), [@hugohaggmark](https://github.com/hugohaggmark)
- **Graphite:** Revert naming convention changes [#117158](https://github.com/grafana/grafana/pull/117158), [@aangelisc](https://github.com/aangelisc)
- **Heatmap:** Add timeRangePan [#113889](https://github.com/grafana/grafana/pull/113889), [@drew08t](https://github.com/drew08t)
- **Heatmap:** Support for linear y axis [#113337](https://github.com/grafana/grafana/pull/113337), [@leeoniya](https://github.com/leeoniya)
- **I18n:** Ignore dist folder in packages when extracting translations [#116532](https://github.com/grafana/grafana/pull/116532), [@aocenas](https://github.com/aocenas)
- **IAM:** Optionally make refresh tokens required if use_refresh_token is enabled [#114174](https://github.com/grafana/grafana/pull/114174), [@cinaglia](https://github.com/cinaglia)
- **InteractiveTable:** Extend sort options with `disableSortRemove` and `sortDescFirst` [#115352](https://github.com/grafana/grafana/pull/115352), [@mikkancso](https://github.com/mikkancso)
- **InteractiveTable:** Prevent reset to first page after `data` property change unless `autoResetPage` property is specified [#117546](https://github.com/grafana/grafana/pull/117546), [@darrenjaneczek](https://github.com/darrenjaneczek)
- **Library Elements:** Deprecate folderFilter query param; update docs for folderFilterUIDs [#116048](https://github.com/grafana/grafana/pull/116048), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **Live:** Add configuration for client_queue_max_size [#114225](https://github.com/grafana/grafana/pull/114225), [@itsgareth](https://github.com/itsgareth)
- **Live:** Use namespace rather than OrgID [#117275](https://github.com/grafana/grafana/pull/117275), [@ryantxu](https://github.com/ryantxu)
- **Log Line Context:** Internally manage displayed fields [#116912](https://github.com/grafana/grafana/pull/116912), [@matyax](https://github.com/matyax)
- **Logs Panel:** Added support for transformations when using infinite scrolling [#116528](https://github.com/grafana/grafana/pull/116528), [@matyax](https://github.com/matyax)
- **Logs Panel:** Added support for unwrapped logs with optional columns for displayed fields [#117402](https://github.com/grafana/grafana/pull/117402), [@matyax](https://github.com/matyax)
- **Logs Panel:** Integrate client-side search with Popover Menu [#114653](https://github.com/grafana/grafana/pull/114653), [@colega](https://github.com/colega)
- **Logs Volume:** Show visible range of logs in Explore [#114501](https://github.com/grafana/grafana/pull/114501), [@matyax](https://github.com/matyax)
- **Logs:** Cell format value on inspect should use Code view for arrays, objects, and JSON strings [#115037](https://github.com/grafana/grafana/pull/115037), [@L2D2Grafana](https://github.com/L2D2Grafana)
- **Logs:** Feature flag logRowsPopoverMenu removed [#113583](https://github.com/grafana/grafana/pull/113583), [@matyax](https://github.com/matyax)
- **Logs:** Feature flag logsInfiniteScrolling removed [#113585](https://github.com/grafana/grafana/pull/113585), [@matyax](https://github.com/matyax)
- **Logs:** Improved flexibility of `hasSupplementaryQuerySupport` [#115348](https://github.com/grafana/grafana/pull/115348), [@aangelisc](https://github.com/aangelisc)
- **Logs:** Persist sort order in the Explore URL [#114350](https://github.com/grafana/grafana/pull/114350), [@matyax](https://github.com/matyax)
- **Loki:** Apply default_manage_alerts_ui_toggle config [#112297](https://github.com/grafana/grafana/pull/112297), [@416e64726579](https://github.com/416e64726579)
- **MSSQL:** Current-user authentication [#113977](https://github.com/grafana/grafana/pull/113977), [@aangelisc](https://github.com/aangelisc)
- **MetricsDrilldown:** Remove `exploreMetricsRelatedLogs` feature toggle [#116090](https://github.com/grafana/grafana/pull/116090), [@NWRichmond](https://github.com/NWRichmond)
- **MySQL:** Add variable query editor support [#116900](https://github.com/grafana/grafana/pull/116900), [@yesoreyeram](https://github.com/yesoreyeram)
- **NPM:** Dispatch to plugin-tools on e2e-selectors changes [#115218](https://github.com/grafana/grafana/pull/115218), [@sunker](https://github.com/sunker)
- **New Logs Panel:** Enable new visualization by default [#113340](https://github.com/grafana/grafana/pull/113340), [@matyax](https://github.com/matyax)
- **News Panel:** Modify pubDate logic to use updated date as fallback [#113329](https://github.com/grafana/grafana/pull/113329), [@swiffer](https://github.com/swiffer)
- **Node Graph:** Use first numeric field as fallback for main stat [#116530](https://github.com/grafana/grafana/pull/116530), [@ifrost](https://github.com/ifrost)
- **PDFTables:** Dynamically shrink font to try and fit whole table in pdf page width (Enterprise)
- **Page:** Background prop to support canvas background for standard layout pages [#111174](https://github.com/grafana/grafana/pull/111174), [@torkelo](https://github.com/torkelo)
- **Panel Menu:** Allow using icons for link extensions [#114836](https://github.com/grafana/grafana/pull/114836), [@leventebalogh](https://github.com/leventebalogh)
- **Panel visualizations:** Focus on search input when changing visualizations [#115484](https://github.com/grafana/grafana/pull/115484), [@idastambuk](https://github.com/idastambuk)
- **PanelChrome:** Enable new panel padding by default [#114492](https://github.com/grafana/grafana/pull/114492), [@torkelo](https://github.com/torkelo)
- **PanelChrome:** Feature toggle increased panel header height and padding [#112613](https://github.com/grafana/grafana/pull/112613), [@torkelo](https://github.com/torkelo)
- **Playlists:** Graduate to v1 apis [#117638](https://github.com/grafana/grafana/pull/117638), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **Plugin Metrics:** Improve metrics on long duration queries within grafana [#116371](https://github.com/grafana/grafana/pull/116371), [@sarahzinger](https://github.com/sarahzinger)
- **PostgreSQL:** Add variable query editor support [#115974](https://github.com/grafana/grafana/pull/115974), [@yesoreyeram](https://github.com/yesoreyeram)
- **PostgreSQL:** Remove feature toggle `postgresDSUsePGX` [#113675](https://github.com/grafana/grafana/pull/113675), [@zoltanbedi](https://github.com/zoltanbedi)
- **Preferences:** Add API validation and update documentation [#116045](https://github.com/grafana/grafana/pull/116045), [@stephaniehingtgen](https://github.com/stephaniehingtgen)
- **Prometheus Dashboards:** Use $\_\_rate_interval instead of hardcoded value [#111899](https://github.com/grafana/grafana/pull/111899), [@attu0](https://github.com/attu0)
- **Prometheus:** Add variable job and replaced hardcoded values in prometheus 2.0 stats dashboard [#115916](https://github.com/grafana/grafana/pull/115916), [@saurabh007007](https://github.com/saurabh007007)
- **Prometheus:** Hide 'Kick start your query' button for existing queries [#113980](https://github.com/grafana/grafana/pull/113980), [@priyansh3006](https://github.com/priyansh3006)
- **Prometheus:** Introduce failsafe PromQueryFormat unmarshalling [#116670](https://github.com/grafana/grafana/pull/116670), [@itsmylife](https://github.com/itsmylife)
- **Prometheus:** Introduce filtering /series endpoint for prometheus versions that don't support match[] parameter [#116648](https://github.com/grafana/grafana/pull/116648), [@itsmylife](https://github.com/itsmylife)
- **Prometheus:** Optimize regex pattern for multi-value label matchers [#116233](https://github.com/grafana/grafana/pull/116233), [@Krishnachaitanyakc](https://github.com/Krishnachaitanyakc)
- **Prometheus:** Revert "Prometheus: Make sure "Min Step" has precedence (#115941)" [#116959](https://github.com/grafana/grafana/pull/116959), [@ellisda](https://github.com/ellisda)
- **Provisioning:** Enable editing dashboard via JSON model [#115420](https://github.com/grafana/grafana/pull/115420), [@Clarity-89](https://github.com/Clarity-89)
- **Provisioning:** Integrate GH app connections into the wizard flow [#116547](https://github.com/grafana/grafana/pull/116547), [@Clarity-89](https://github.com/Clarity-89)
- **Pyroscope:** Exemplar support for series queries [#113926](https://github.com/grafana/grafana/pull/113926), [@alsoba13](https://github.com/alsoba13)
- **Query Editor:** Add Query Options footer and sidebar for new query editor [#117403](https://github.com/grafana/grafana/pull/117403), [@Develer](https://github.com/Develer)
- **QueryEditorRows:** Clear hideSeriesFrom override on query edit [#114315](https://github.com/grafana/grafana/pull/114315), [@Sergej-Vlasov](https://github.com/Sergej-Vlasov)
- **Reporting:** Productize reporting retries feature [#117378](https://github.com/grafana/grafana/pull/117378), [@macabu](https://github.com/macabu)
- **Reporting:** Remove newPDFRendering feature flag, stabilising it (Enterprise)
- **Reporting:** Support editing template variables in the form for dashboards v2 (Enterprise)
- **Restore dashboards:** Improve permissions [#116266](https://github.com/grafana/grafana/pull/116266), [@Clarity-89](https://github.com/Clarity-89)
- **SQL Expressions:** Add "NOT" keyword to allow list [#116802](https://github.com/grafana/grafana/pull/116802), [@net0pyr](https://github.com/net0pyr)
- **SQLDataSource:** Use UID rather than internal ID [#116461](https://github.com/grafana/grafana/pull/116461), [@ryantxu](https://github.com/ryantxu)
- **SQLExpressions:** Add new schema inspector panel [#113545](https://github.com/grafana/grafana/pull/113545), [@alexjonspencer1](https://github.com/alexjonspencer1)
- **Scopes:** Scope input UI update [#114002](https://github.com/grafana/grafana/pull/114002), [@torkelo](https://github.com/torkelo)
- **Search:** Move experimental panelTitleSearch from searchV2 to unified search [#116326](https://github.com/grafana/grafana/pull/116326), [@ryantxu](https://github.com/ryantxu)
- **SearchAPI:** Return "shared with me" children based on the permission query param [#116254](https://github.com/grafana/grafana/pull/116254), [@aocenas](https://github.com/aocenas)
- **Secrets Keeper:** Add secretsKeeperUI feature flag [#117427](https://github.com/grafana/grafana/pull/117427), [@ericrshields](https://github.com/ericrshields)
- **Secrets Keeper:** UI shell with tab navigation (Enterprise)
- **Security:** Sanitize TraceView html [#117853](https://github.com/grafana/grafana/pull/117853), [@github-actions[bot]](https://github.com/github-actions[bot])
- **Security:** Use dashboard timerange if time selection disabled [#117854](https://github.com/grafana/grafana/pull/117854), [@dana-axinte](https://github.com/dana-axinte)
- **SelectBase:** Use standard portal container [#114844](https://github.com/grafana/grafana/pull/114844), [@torkelo](https://github.com/torkelo)
- **Short URL:** Change default expiration to never [#115029](https://github.com/grafana/grafana/pull/115029), [@nmarrs](https://github.com/nmarrs)
- **Sidebar:** A new reusable component for side toolbars and panes [#114141](https://github.com/grafana/grafana/pull/114141), [@torkelo](https://github.com/torkelo)
- **Span Details:** Two-column view [#112856](https://github.com/grafana/grafana/pull/112856), [@ifrost](https://github.com/ifrost)
- **Sparkline:** Improve min/max logic to avoid issues for very narrow deltas [#115030](https://github.com/grafana/grafana/pull/115030), [@fastfrwrd](https://github.com/fastfrwrd)
- **Sparkline:** Prevent infinite loop when rendering a sparkline with a single value [#114203](https://github.com/grafana/grafana/pull/114203), [@fastfrwrd](https://github.com/fastfrwrd)
- **Table:** Add title attribute to make truncated headings legible [#115155](https://github.com/grafana/grafana/pull/115155), [@jesdavpet](https://github.com/jesdavpet)
- **Table:** Clamp Safari exclusions to 26.0 and 26.1 [#114454](https://github.com/grafana/grafana/pull/114454), [@fastfrwrd](https://github.com/fastfrwrd)
- **Table:** Clean up filter popover layout and improve filter selection UX [#114052](https://github.com/grafana/grafana/pull/114052), [@fastfrwrd](https://github.com/fastfrwrd)
- **Table:** Keyboard accessibility for filter [#117354](https://github.com/grafana/grafana/pull/117354), [@fastfrwrd](https://github.com/fastfrwrd)
- **Table:** Remove hardcoded assumption of \_\_nestedFrames field name [#115117](https://github.com/grafana/grafana/pull/115117), [@fastfrwrd](https://github.com/fastfrwrd)
- **TeamFolders:** Show team folders in folder picker [#117381](https://github.com/grafana/grafana/pull/117381), [@aocenas](https://github.com/aocenas)
- **Tempo:** Encode header values before adding them to outgoing context [#117279](https://github.com/grafana/grafana/pull/117279), [@jcolladokuri](https://github.com/jcolladokuri)
- **Tempo:** Remove forwarding incoming and team headers for streaming requests [#117813](https://github.com/grafana/grafana/pull/117813), [@jcolladokuri](https://github.com/jcolladokuri)
- **Theme:** Add breakpoint methods for container queries [#113619](https://github.com/grafana/grafana/pull/113619), [@MattIPv4](https://github.com/MattIPv4)
- **TimePicker:** Show new shortcut for zoom out when experimental flag toggled on [#114506](https://github.com/grafana/grafana/pull/114506), [@jesdavpet](https://github.com/jesdavpet)
- **TimeRange:** Additional keyboard shortcut `t =` to complement `t +` for zoom in [#115022](https://github.com/grafana/grafana/pull/115022), [@jesdavpet](https://github.com/jesdavpet)
- **TimeRange:** Avoid x-axis pan jump caused by data loading latency [#114496](https://github.com/grafana/grafana/pull/114496), [@jesdavpet](https://github.com/jesdavpet)
- **TimeSeries:** X-axis (time range) click-and-drag panning in panel [#112982](https://github.com/grafana/grafana/pull/112982), [@jesdavpet](https://github.com/jesdavpet)
- **Timeline:** Add timeRangePan [#113890](https://github.com/grafana/grafana/pull/113890), [@drew08t](https://github.com/drew08t)
- **Timeseries:** Change mouse cursors to indicate active x-axis and y-axis zoom interactions [#113465](https://github.com/grafana/grafana/pull/113465), [@jesdavpet](https://github.com/jesdavpet)
- **Timeseries:** More nuanced editing of linear threshold to avoid crashes [#112301](https://github.com/grafana/grafana/pull/112301), [@fastfrwrd](https://github.com/fastfrwrd)
- **Trace View:** Span filters updated to use combobox filters [#112287](https://github.com/grafana/grafana/pull/112287), [@adrapereira](https://github.com/adrapereira)
- **Trace datasources:** Add Victoria Metrics support for "traces to metrics" [#114962](https://github.com/grafana/grafana/pull/114962), [@arturminchukov](https://github.com/arturminchukov)
- **Transformers:** Add smoothing transformer [#111077](https://github.com/grafana/grafana/pull/111077), [@vesalaakso-oura](https://github.com/vesalaakso-oura)
- **UI Extensions:** Add `openInNewTab` property to link extensions [#114831](https://github.com/grafana/grafana/pull/114831), [@leventebalogh](https://github.com/leventebalogh)
- **UI:** Use react-table column header types in InteractiveTable with story and tests [#116091](https://github.com/grafana/grafana/pull/116091), [@Alan-eMartin](https://github.com/Alan-eMartin)
- **Unified:** Run resource data migrations at startup [#114857](https://github.com/grafana/grafana/pull/114857), [@RafaelPaulovic](https://github.com/RafaelPaulovic)
- **Viz:** Update OutsideRangePlugin to support single datapoint [#117278](https://github.com/grafana/grafana/pull/117278), [@fastfrwrd](https://github.com/fastfrwrd)

### Bug fixes

- **Alerting:** Add support for client certificate authentication and TLS options to External Alertmanager [#115716](https://github.com/grafana/grafana/pull/115716), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Alerting:** Bug fix for regex matching in Alerts page [#113400](https://github.com/grafana/grafana/pull/113400), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Fix 'Rule group does not exist' error toast (#101949) [#114766](https://github.com/grafana/grafana/pull/114766), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Fix Alerts page filtering [#115178](https://github.com/grafana/grafana/pull/115178), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Fix NotificationPreview permission checking [#114303](https://github.com/grafana/grafana/pull/114303), [@konrad147](https://github.com/konrad147)
- **Alerting:** Fix RuleEditorCloudRules test flakiness in CI [#114695](https://github.com/grafana/grafana/pull/114695), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Fix a race condition panic in ResetStateByRuleUID [#115662](https://github.com/grafana/grafana/pull/115662), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Fix advanced filter not preserving freewords filter in the list view [#114651](https://github.com/grafana/grafana/pull/114651), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Fix alert rule last evaluation duration units [#117814](https://github.com/grafana/grafana/pull/117814), [@JacobsonMT](https://github.com/JacobsonMT)
- **Alerting:** Fix alert rule last evaluation time including scheduling delays [#117819](https://github.com/grafana/grafana/pull/117819), [@JacobsonMT](https://github.com/JacobsonMT)
- **Alerting:** Fix creating a new alert rule vesion when only keep_firing_for changes [#114926](https://github.com/grafana/grafana/pull/114926), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Fix data source recording rules editor [#113363](https://github.com/grafana/grafana/pull/113363), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Fix error when updating Alertmanager config with autogenerated receivers [#113710](https://github.com/grafana/grafana/pull/113710), [@moustafab](https://github.com/moustafab)
- **Alerting:** Fix expression queries when coming from a panel [#114095](https://github.com/grafana/grafana/pull/114095), [@konrad147](https://github.com/konrad147)
- **Alerting:** Fix file import/export of recording rules with target datasource uid [#115663](https://github.com/grafana/grafana/pull/115663), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Fix for fetching evaluation group in new filter [#113694](https://github.com/grafana/grafana/pull/113694), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Fix groupBy in simplified routing UI [#117076](https://github.com/grafana/grafana/pull/117076), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Fix ignored filters when paginating alert rules in the API [#114710](https://github.com/grafana/grafana/pull/114710), [@alexander-akhmetov](https://github.com/alexander-akhmetov)
- **Alerting:** Fix label value dropdown suggestions in alert rule editor [#113702](https://github.com/grafana/grafana/pull/113702), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Fix label value search not filtering results [#116133](https://github.com/grafana/grafana/pull/116133), [@konrad147](https://github.com/konrad147)
- **Alerting:** Fix label values not being shown in the label drop down [#114642](https://github.com/grafana/grafana/pull/114642), [@soniaAguilarPeiron](https://github.com/soniaAguilarPeiron)
- **Alerting:** Fix missing dataSource.type in dsquery enrichers (Enterprise)
- **Alerting:** Fix missing provenance annotation in GetManagedRoute [#117940](https://github.com/grafana/grafana/pull/117940), [@rodrigopk](https://github.com/rodrigopk)
- **Alerting:** Fix to prevent regex escape on search input query [#113734](https://github.com/grafana/grafana/pull/113734), [@laurenashleigh](https://github.com/laurenashleigh)
- **Alerting:** Fix width of the code editor for Alertmanager configurations [#113541](https://github.com/grafana/grafana/pull/113541), [@gillesdemey](https://github.com/gillesdemey)
- **Alerting:** Omit data sources that aren't configured for alerting from search [#116537](https://github.com/grafana/grafana/pull/116537), [@gillesdemey](https://github.com/gillesdemey)
- **Alerting:** Patch missing expression model refIds [#114477](https://github.com/grafana/grafana/pull/114477), [@gillesdemey](https://github.com/gillesdemey)
- **Alerting:** Remove unknown state filter [#114143](https://github.com/grafana/grafana/pull/114143), [@konrad147](https://github.com/konrad147)
- **Alerting:** Update alert_rule table to fix paginated results [#111336](https://github.com/grafana/grafana/pull/111336), [@moustafab](https://github.com/moustafab)
- **Alerting:** Update alert_rule table to fix paginated results [#111336](https://github.com/grafana/grafana/pull/111336), [@moustafab](https://github.com/moustafab)
- **Alerting:** Update alert_rule table to fix paginated results [#111336](https://github.com/grafana/grafana/pull/111336), [@moustafab](https://github.com/moustafab)
- **AnalyticsSummaries:** Fix dashboard rollup not resetting "last X days" metrics to zero (Enterprise)
- **AnalyticsSummaries:** Fix dashboard rollup totals resetting incorrectly (Enterprise)
- **Auth:** Fix inconsistent symbol validation by allowing underscore "\_" in strong password policy [#114571](https://github.com/grafana/grafana/pull/114571), [@ooye-sanket](https://github.com/ooye-sanket)
- **Azure:** Fix `dcount` aggregation [#114666](https://github.com/grafana/grafana/pull/114666), [@aangelisc](https://github.com/aangelisc)
- **Azure:** Fix `percentile` syntax [#114665](https://github.com/grafana/grafana/pull/114665), [@aangelisc](https://github.com/aangelisc)
- **BrowseDashboards:** Fix nested folder's parent folder dropped after rename folder title [#116223](https://github.com/grafana/grafana/pull/116223), [@ywzheng1](https://github.com/ywzheng1)
- **Canvas:** Fix image loading when icon element SVG defined by field mappings [#115748](https://github.com/grafana/grafana/pull/115748), [@jesdavpet](https://github.com/jesdavpet)
- **CloudWatch:** Fix error source for some query errors [#115791](https://github.com/grafana/grafana/pull/115791), [@njvrzm](https://github.com/njvrzm)
- **CloudWatch:** Fix template variable intepolation for metrics queries [#116574](https://github.com/grafana/grafana/pull/116574), [@kevinwcyu](https://github.com/kevinwcyu)
- **Cloudwatch:** Add log group prefix and all-log queries [#117210](https://github.com/grafana/grafana/pull/117210), [@kevinwcyu](https://github.com/kevinwcyu)
- **Custom branding:** Correctly override bouncing loader [#115871](https://github.com/grafana/grafana/pull/115871), [@ashharrison90](https://github.com/ashharrison90)
- **Dashboard datasource:** Fix library panels not tracked in mixed queries [#112959](https://github.com/grafana/grafana/pull/112959), [@axelavargas](https://github.com/axelavargas)
- **Dashboard:** Fix for missing focus style on DataLinkInput component [#117095](https://github.com/grafana/grafana/pull/117095), [@DivyamUp14](https://github.com/DivyamUp14)
- **Dashboard:** Fixes performance issuing saving multiple times [#117230](https://github.com/grafana/grafana/pull/117230), [@torkelo](https://github.com/torkelo)
- **Dashboards:** Fix timeseries off-by N time shift bug after mouse x-axis zoom in panel [#113821](https://github.com/grafana/grafana/pull/113821), [@jesdavpet](https://github.com/jesdavpet)
- **Datasources:** Fix permissions cleanup when deleting datasource by name [#117289](https://github.com/grafana/grafana/pull/117289), [@mihai-turdean](https://github.com/mihai-turdean)
- **Dynamic Dashboards:** Fix Content outline not being scrollable [#115827](https://github.com/grafana/grafana/pull/115827), [@AyushKaithwas](https://github.com/AyushKaithwas)
- **Dynamic Dashboards:** Fix legend click opening panel edit sidebar [#116476](https://github.com/grafana/grafana/pull/116476), [@AyushKaithwas](https://github.com/AyushKaithwas)
- **Dynamic Dashboards:** Fix show/hide rules when template variable has "All" selected [#116529](https://github.com/grafana/grafana/pull/116529), [@AyushKaithwas](https://github.com/AyushKaithwas)
- **Elasticsearch:** Fix incorrect log level parsing for nested fields [#116637](https://github.com/grafana/grafana/pull/116637), [@adamyeats](https://github.com/adamyeats)
- **Fix:** Don't reuse go-plugin config [#117877](https://github.com/grafana/grafana/pull/117877), [@njvrzm](https://github.com/njvrzm)
- **Fix:** Ensure clone handles functions properly [#116521](https://github.com/grafana/grafana/pull/116521), [@sunker](https://github.com/sunker)
- **Fix:** Make plugin.json routes[].path field required [#116286](https://github.com/grafana/grafana/pull/116286), [@s4kh](https://github.com/s4kh)
- **Fix:** Return auth labels from `/api/users/lookup` [#113584](https://github.com/grafana/grafana/pull/113584), [@mgyongyosi](https://github.com/mgyongyosi)
- **Fix:** Show deprecated badge if installed plugin version is deprecated [#117101](https://github.com/grafana/grafana/pull/117101), [@s4kh](https://github.com/s4kh)
- **Folders:** Make `listFolders` call correct API and fix tags sorting [#114181](https://github.com/grafana/grafana/pull/114181), [@tomratcliffe](https://github.com/tomratcliffe)
- **GrafanaUI:** Fix iconPlacement prop not being respected in LinkButton [#113708](https://github.com/grafana/grafana/pull/113708), [@ckbedwell](https://github.com/ckbedwell)
- **Graphite:** Use target as name for aliased queries [#116213](https://github.com/grafana/grafana/pull/116213), [@aangelisc](https://github.com/aangelisc)
- **Histogram:** Fix runaway bucket densification with extremely sparse + large datasets [#114557](https://github.com/grafana/grafana/pull/114557), [@jesdavpet](https://github.com/jesdavpet)
- **Icon:** Fix SVG not updating when icon name is changed quickly [#117584](https://github.com/grafana/grafana/pull/117584), [@joshhunt](https://github.com/joshhunt)
- **Jaeger:** Fix variable interpolation in query input [#115513](https://github.com/grafana/grafana/pull/115513), [@dolph](https://github.com/dolph)
- **Notifications:** Prevent triggering duplicate notifications [#114497](https://github.com/grafana/grafana/pull/114497), [@Alan-eMartin](https://github.com/Alan-eMartin)
- **Plugins Preinstall:** Fix URL parsing when includes basic auth [#115143](https://github.com/grafana/grafana/pull/115143), [@andresmgot](https://github.com/andresmgot)
- **Plugins:** Add PluginContext to plugins when scenes is disabled [#114989](https://github.com/grafana/grafana/pull/114989), [@hugohaggmark](https://github.com/hugohaggmark)
- **Plugins:** Datasource breadcrumb link should link to settings tab [#113862](https://github.com/grafana/grafana/pull/113862), [@wbrowne](https://github.com/wbrowne)
- **Plugins:** Fix frontend sandbox crash on Firefox with missing browser APIs [#116422](https://github.com/grafana/grafana/pull/116422), [@academo](https://github.com/academo)
- **Postgresql:** Fix variable interpolation logic when the variable has multiple values [#114058](https://github.com/grafana/grafana/pull/114058), [@itsmylife](https://github.com/itsmylife)
- **Prometheus:** Fix broken hardcoded override in Prometheus 2.0 dashboard [#116940](https://github.com/grafana/grafana/pull/116940), [@saurabh007007](https://github.com/saurabh007007)
- **Prometheus:** Make sure "Min Step" has precedence for a longer time windows [#115941](https://github.com/grafana/grafana/pull/115941), [@itsmylife](https://github.com/itsmylife)
- **QueryVariableForm:** Refil query variable query on default data source update [#114491](https://github.com/grafana/grafana/pull/114491), [@Sergej-Vlasov](https://github.com/Sergej-Vlasov)
- **RBAC:** Correctly display the new roles after updating user, service account and team roles [#113783](https://github.com/grafana/grafana/pull/113783), [@IevaVasiljeva](https://github.com/IevaVasiljeva)
- **RBAC:** Fix rolepicker autoclosing [#116726](https://github.com/grafana/grafana/pull/116726), [@yudintsevegor](https://github.com/yudintsevegor)
- **Reporting:** Fix PDF report header translation for non-English locales (Enterprise)
- **Reporting:** Fix bug limiting email address length in recipient field (Enterprise)
- **SQL Expressions:** Fix alerts with sql expressions that have a cte [#114852](https://github.com/grafana/grafana/pull/114852), [@sarahzinger](https://github.com/sarahzinger)
- **SubMenu:** Prevent menu positioning itself offscreen [#116907](https://github.com/grafana/grafana/pull/116907), [@ashharrison90](https://github.com/ashharrison90)
- **Tempo:** Correctly escape/unescape tag when looking for tag values [#114275](https://github.com/grafana/grafana/pull/114275), [@joe-elliott](https://github.com/joe-elliott)
- **Tempo:** Fix multiple streaming TraceQL metrics queries being conflated into one [#114360](https://github.com/grafana/grafana/pull/114360), [@joe-elliott](https://github.com/joe-elliott)
- **TimeSeries:** Fix truncated label text in legend table mode [#115647](https://github.com/grafana/grafana/pull/115647), [@jesdavpet](https://github.com/jesdavpet)
- **Trace View:** Correctly handle span and service name in span filters [#115215](https://github.com/grafana/grafana/pull/115215), [@adrapereira](https://github.com/adrapereira)
- **UI:** Fix number fields unexpectedly changing when scrolling [#117264](https://github.com/grafana/grafana/pull/117264), [@bittoby](https://github.com/bittoby)

### Breaking changes

- **Plugins:** Prevent passing host environment variables to plugin processes by default [#113412](https://github.com/grafana/grafana/pull/113412), [@wbrowne](https://github.com/wbrowne)

### Plugin development fixes & changes

- **Slider:** Add support for decimal values [#113473](https://github.com/grafana/grafana/pull/113473), [@HarshadaGawas05](https://github.com/HarshadaGawas05)
- **Toggletip:** Ensure consistent positioning in all scenarios [#114085](https://github.com/grafana/grafana/pull/114085), [@ashharrison90](https://github.com/ashharrison90)
- **ToolbarButton:** Require `tooltip` or `aria-label` if no children are present [#114097](https://github.com/grafana/grafana/pull/114097), [@ashharrison90](https://github.com/ashharrison90)


================================================================================

# 12.4.1

Tag: v12.4.1
URL: https://github.com/grafana/grafana/releases/tag/v12.4.1

[Download page](https://grafana.com/grafana/download/12.4.1)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **AccessControl:** Invalidate scope resolver cache on datasource deletion [#118741](https://github.com/grafana/grafana/pull/118741), [@mihai-turdean](https://github.com/mihai-turdean)
- **Go:** Update to 1.25.8 [#119693](https://github.com/grafana/grafana/pull/119693), [@macabu](https://github.com/macabu)
- **Rendering:** Add support for custom CA certs in Image Renderer [#118859](https://github.com/grafana/grafana/pull/118859), [@mrevutskyi](https://github.com/mrevutskyi)

### Bug fixes

- **AccessControl:** Fix test utility for datasource deletion permissions cleanup (Enterprise)
- **Alerting:** Change scope for testing new receivers to use supported resource type. [#118495](https://github.com/grafana/grafana/pull/118495), [@yuri-tceretian](https://github.com/yuri-tceretian)
- **Alerting:** Fix CollateAlertRuleGroup migration for MariaDB compatibility [#119028](https://github.com/grafana/grafana/pull/119028), [@alexander-akhmetov](https://github.com/alexander-akhmetov)


================================================================================

# 12.4.2

Tag: v12.4.2
URL: https://github.com/grafana/grafana/releases/tag/v12.4.2

[Download page](https://grafana.com/grafana/download/12.4.2)
[What's new highlights](https://grafana.com/docs/grafana/latest/whatsnew/)

### Features and enhancements

- **Analytics tab:** Improve voice over accessibility (Enterprise)
- **Dashboards a11y:** Do not open time zonemenu on focus [#120388](https://github.com/grafana/grafana/pull/120388), [@idastambuk](https://github.com/idastambuk)
- **Dashboards:** Resolve display names by identity in version history [#120273](https://github.com/grafana/grafana/pull/120273), [@ivanortegaalba](https://github.com/ivanortegaalba)
- **Plugins:** Forward AWS SDK credential chain env vars to external AWS plugins [#120209](https://github.com/grafana/grafana/pull/120209), [@kevinwcyu](https://github.com/kevinwcyu)
- **Public Dashboards:** Prevent unintended CRUD operations from different orgs [#120457](https://github.com/grafana/grafana/pull/120457), [@mmandrus](https://github.com/mmandrus)

### Bug fixes

- **IAM:** Handle NULL team_member.external column to fix dashboard loading [#120179](https://github.com/grafana/grafana/pull/120179), [@difro](https://github.com/difro)
- **Plugins:** Fix installer IsDisabled condition [#120568](https://github.com/grafana/grafana/pull/120568), [@andresmgot](https://github.com/andresmgot)
- **Plugins:** Forward PLUGIN_UNIX_SOCKET_DIR to plugin processes to fix tmp dir in restricted environments [#120275](https://github.com/grafana/grafana/pull/120275), [@HarshadaGawas05](https://github.com/HarshadaGawas05)
- **Security:** Fixes CVE-2026-27876
- **Security:** Fixes CVE-2026-27877
- **Security:** Fixes CVE-2026-28375
- **Security:** Fixes CVE-2026-27879
- **Security:** Fixes CVE-2026-27880
- **Security:** Fixes CVE-2026-27876
- **Security:** Fixes CVE-2026-33375

