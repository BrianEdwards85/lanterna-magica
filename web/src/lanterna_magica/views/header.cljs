(ns lanterna-magica.views.header
  (:require [lanterna-magica.bp :as bp]
            [lanterna-magica.routes :as routes]
            [lanterna-magica.subs :as subs]
            [re-frame.core :as rf]))

(defn header []
  (let [route-name @(rf/subscribe [::subs/current-route-name])]
    [bp/navbar {:class "mb-4"}
     [bp/navbar-group {:align "left"}
      [:a {:href  (routes/href :route/home)
           :class "flex items-center no-underline"
           :style {:color "inherit"}}
       [bp/icon {:icon "cog" :intent "primary" :class "mr-2"}]
       [bp/navbar-heading "Lanterna Magica"]]
      [bp/navbar-divider]
      [bp/button {:icon     "tag"
                  :text     "Dimensions"
                  :minimal  true
                  :active   (= route-name :route/dimensions)
                  :class    "mobile-icon-only"
                  :on-click #(routes/navigate! :route/dimensions)}]
      [bp/button {:icon     "variable"
                  :text     "Shared Values"
                  :minimal  true
                  :active   (= route-name :route/shared-values)
                  :class    "mobile-icon-only"
                  :on-click #(routes/navigate! :route/shared-values)}]
      [bp/button {:icon     "document"
                  :text     "Configurations"
                  :minimal  true
                  :active   (= route-name :route/configurations)
                  :class    "mobile-icon-only"
                  :on-click #(routes/navigate! :route/configurations)}]]]))
