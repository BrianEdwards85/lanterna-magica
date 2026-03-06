(ns lanterna-magica.views.home
  (:require [lanterna-magica.bp :as bp]
            [lanterna-magica.routes :as routes]
            [lanterna-magica.subs :as subs]
            [re-frame.core :as rf]))

(defn- count-card [title icon-name route-key sub-key]
  (let [data  @(rf/subscribe [sub-key])
        edges (:edges data)]
    [:div {:class "bp6-card bp6-interactive p-4 cursor-pointer"
           :on-click #(routes/navigate! route-key)}
     [:div.flex.items-center.gap-3.mb-2
      [bp/icon {:icon icon-name :size 20}]
      [:h3.text-lg.font-semibold title]]
     [:p.text-sm.text-tn-fg-muted
      (str (count edges) " loaded")]]))

(defn home-screen []
  [:div.p-8.max-w-4xl.mx-auto
   [:h1.text-2xl.font-bold.mb-2 "Lanterna Magica"]
   [:p.text-tn-fg-muted.mb-8
    "Configuration management for services across environments."]
   [:div.grid.grid-cols-1.md:grid-cols-2.gap-4
    [count-card "Services"       "applications"  :route/services       ::subs/services-page]
    [count-card "Environments"   "globe-network" :route/environments   ::subs/environments-page]
    [count-card "Shared Values"  "variable"      :route/shared-values  ::subs/shared-values-page]
    [count-card "Configurations" "document"      :route/configurations ::subs/configurations-page]]])
