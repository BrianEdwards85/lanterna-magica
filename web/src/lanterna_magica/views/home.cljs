(ns lanterna-magica.views.home
  (:require [lanterna-magica.bp :as bp]
            [lanterna-magica.routes :as routes]))

(defn- nav-card [title description icon-name route-key]
  [:div {:class "bp6-card bp6-interactive p-4 cursor-pointer"
         :on-click #(routes/navigate! route-key)}
   [:div.flex.items-center.gap-3.mb-2
    [bp/icon {:icon icon-name :size 20}]
    [:h3.text-lg.font-semibold title]]
   [:p.text-sm.text-tn-fg-muted.mb-0 description]])

(defn home-screen []
  [:div.p-8.max-w-4xl.mx-auto
   [:h1.text-2xl.font-bold.mb-2 "Lanterna Magica"]
   [:p.text-tn-fg-muted.mb-8
    "Configuration management for services across environments."]
   [:div.grid.grid-cols-1.md:grid-cols-2.gap-4
    [nav-card "Services"       "Manage registered services"             "applications"  :route/services]
    [nav-card "Environments"   "Manage deployment environments"        "globe-network" :route/environments]
    [nav-card "Shared Values"  "Manage shared configuration values"    "variable"      :route/shared-values]
    [nav-card "Configurations" "View and create service configurations" "document"      :route/configurations]]])
